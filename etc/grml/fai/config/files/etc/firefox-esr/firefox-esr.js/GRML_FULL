/* Added by grml-live */

// This is the Debian specific preferences file for Firefox ESR
// You can make any change in here, it is the purpose of this file.
// You can, with this file and all files present in the
// /etc/firefox-esr directory, override any preference you can see in
// about:config.
//
// Note that lockPref is allowed in these preferences files if you
// don't want users to be able to override some preferences.

pref("extensions.update.enabled", true);

// Use LANG environment variable to choose locale
pref("intl.locale.matchOS", true);

// Disable default browser checking.
pref("browser.shell.checkDefaultBrowser", false);

// Avoid openh264 being downloaded.
pref("media.gmp-manager.url.override", "data:text/plain,");

// Disable openh264.
pref("media.gmp-gmpopenh264.enabled", false);

// Default to classic view for about:newtab
sticky_pref("browser.newtabpage.enhanced", false);

// Disable health report upload
pref("datareporting.healthreport.uploadEnabled", false);

// Grml specific configuration
pref("startup.homepage_welcome_url", "file:///usr/share/doc/grml-docs/startpage.html");
pref("startup.homepage_welcome_url.additional", "https://grml.org/");
