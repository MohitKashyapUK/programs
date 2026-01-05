// Background service worker
// Currently, most logic is handled via declarativeNetRequest dynamic rules
// which are updated from the options page.

chrome.runtime.onInstalled.addListener(() => {
    console.log("Website Blocker Extension Installed");
});
