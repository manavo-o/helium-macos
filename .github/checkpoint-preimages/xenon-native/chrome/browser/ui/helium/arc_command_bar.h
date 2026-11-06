// Copyright 2026 The Helium Authors
// You can use, redistribute, and/or modify this source code under
// the terms of the GPL-3.0 license that can be found in the LICENSE file.

#ifndef CHROME_BROWSER_UI_HELIUM_ARC_COMMAND_BAR_H_
#define CHROME_BROWSER_UI_HELIUM_ARC_COMMAND_BAR_H_
#include <string>

class BrowserWindowInterface;
namespace content { class WebContents; }

namespace helium {

// Only the built-in home surfaces; extension new-tab pages retain their URL.
bool IsArcHome(content::WebContents* contents);
void ShowArcAppearance(BrowserWindowInterface* browser);
void SetArcCommandBarInputForTesting(BrowserWindowInterface* browser, const std::u16string& text);

// Opens the deferred-tab command palette. Returns false if no suitable browser
// view is available, allowing the caller to retain normal new-tab behavior.
bool ShowArcCommandBar(BrowserWindowInterface* browser);

}  // namespace helium

#endif  // CHROME_BROWSER_UI_HELIUM_ARC_COMMAND_BAR_H_
