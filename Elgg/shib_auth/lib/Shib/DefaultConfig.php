<?php

/*
 * Default config class distributed with mod/shib_auth
 */
class Shib_DefaultConfig implements Shib_IConfig {

    /*
     * If true, only users who registered via shib_auth will be able to login
     * via shib_auth.
     *
     * NOTE: Setting this to false would allow a Shibboleth user to login to
     * an existing Elgg account regardless of if they actually owned the account.
     * I.e. The Shibboleth user doesn't need to know the Elgg account's password.
     *
     * If you set this to false or remove it from your config class, be sure
     * to include logic to ensure that the Shibboleth user matches the Elgg user.
     *
     * @var bool
     */
    protected $_requireShibAuthFlag = true;

    /**
     * @var Shib_Core
     */
    protected $core;

    // Constant indicating where the terms and conditions service lives
    protected $tandcServer  =  "https://collaboration.canarie.ca/terms";

    // URLs to redirect to if the terms and conditions are accepted or declined respectively
    // There's no really good way to get these dynamically, so I'll hard code for now.

    // URL to forward to if the terms and conditions are accepted. Here;s how this works:
    // After the user has provided credentials to Shibboleth, the browser is re-directed to 
    // mod/shib_auth/validate (located in Core.php). The validate handler calls preLogin() 
    // below. preLogin() checks to see if the user has previously accepted the terms and
    // conditions. If they have, control is simply returned to the validate handler. It is not until
    // this point that the user is fully logged on to Elgg. If the user has not accepted the terms
    // and conditions, control is passed to the terms and conditions service, with instructions
    // to return to the validate URL if the user accepts. This time, when preLogin()
    // checks to see if the user has accepted the terms and conditions, the result will be
    // yes and control will be returned to the validate handler to complete the Elgg login. 
    protected $acceptURL   = "https://collaboration.canarie.ca/elgg/mod/shib_auth/validate";

    // If the user does not accept the terms and conditions, just forward the browser to the
    // Elgg main page. Since the Elgg part of the login process has not been completed, the
    // user will not be logged on.
    protected $declineURL = "https://collaboration.canarie.ca/elgg";



    public function getLoginPersistent()
    {
        return false;
    }

    public function getAllowAccountsWithSameEmail()
    {
        return false;
    }

    public function getRegistationDetails()
    {
        $details = new Shib_RegDetails();
        $details->name = $_SERVER['shib-fullname'];
        $details->mail = $_SERVER['shib-mail'];
        return $details;
    }

    public function getShibUsername()
    {
        return isset($_SERVER['shib-uid'])
            ? $_SERVER['shib-uid']
            : '';
    }

    public function setCore(Shib_Core $core)
    {
        $this->core = $core;
    }

    public function belongsToShibUser(ElggUser $user)
    {
        if ($this->_requireShibAuthFlag) {
            return (bool) $user->getPrivateSetting('shib_auth');
        } else {
            return true;
        }
    }

    public function postRegister(ElggUser $user)
    {
        $user->setPrivateSetting('shib_auth', '1');
        system_message(elgg_echo("registerok", array(elgg_get_site_entity()->name)));
    }

    public function postLogin(ElggUser $user)
    {
        system_message(elgg_echo('loginok'));
    }

    public function postLogout()
    {
        $this->core->removeSpCookies();
    }

    /*
     * Called if the Elgg user fails belongsToShibUser()
     *
     * @param ElggUser $user
     */
    public function onInvalidUser(ElggUser $user)
    {
        register_error("The system failed to log you in as '" . $this->getShibUsername() . "'."
            . " Please ask your site administrator for assistance.");
        forward();
    }

    /*
     * Called if is_loggedin() is true at very beginning of Shib->validate()
     */
    public function loggedInAlready()
    {
        forward('activity');
    }

    /*
     * Called if register_user() fails
     */
    public function onRegistrationFailure()
    {
        register_error("The system failed to register you as '" . $this->getShibUsername() . "'."
            . " Please ask your site administrator for assistance.");
        forward();
    }

    /*
     * Called if sniffUsername() fails to populate $this->username
     */
    public function onEmptyUsername()
    {
        register_error("Shibboleth is not correctly configured."
            . " Please ask your site administrator for assistance.");
        forward();
    }

    /*
     * During registration, called if getRegistationDetails() doesn't return a 'mail'
     */
    public function onEmptyRegistrationMail()
    {
        register_error("Shibboleth is not correctly configured to include your e-mail address.");
    }

    /*
     * During registration, called if getRegistationDetails() doesn't return a 'name'
     */
    public function onEmptyRegistrationName()
    {
        register_error("Shibboleth is not correctly configured to include your name.");
    }

    /*
     * Called before Elgg user is logged in. If you don't want the user to login,
     * redirect away...
     *
     * @param ElggUser $user
     */
    public function preLogin(ElggUser $user)
    {
	// Call the terms and conditions service to see if the user attempting
        // to log on has accepted the current version.
        $json = file_get_contents($this->tandcServer . "/utils/signed?user=$user");
        $response = json_decode($json);
            
        // 'user' from response should aways match $user, but worth checking anyway just in case
        // there's a problem with the T&C service. If user hasn't accepted the
        // terms and conditions, log them off and display an appropriate message.
        if (($response->{'user'} != $user) || ($response->{'signed'} != true))
        {
            // Forward us to the Terms and Conditions acceptance page. If
            // user accepts, send us back here and the check above will fail.
            // If the user declines, send us back to the main page. User
            // will not be logged on at this point.
                
            // Get the Elgg user definition structure for this user so we can display
            // the terms and conditions in the appropriate language. Note that the
            // browser's language setting will override this.
	    $elggUser = get_user_by_username($user);
            $lang = $elggUser->language;

            if ($lang == 'fr')
            {
                forward ($this->tandcServer . "/fr/tc/?user=$user&accept=$this->acceptURL&decline=$this->declineURL");
            }
            else
            {
                forward ($this->tandcServer . "/tc/?user=$user&accept=$this->acceptURL&decline=$this->declineURL");     
            }
        }                
    }

    /*
     * Called before Elgg's logout() is called (if user was logged in)
     *
     * @param ElggUser $user
     */
    public function preLogout(ElggUser $user)
    {

    }
}
