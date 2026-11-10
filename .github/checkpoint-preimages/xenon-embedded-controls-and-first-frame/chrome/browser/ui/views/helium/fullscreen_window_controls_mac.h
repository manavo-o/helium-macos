// Copyright 2026 The Helium Authors
// You can use, redistribute, and/or modify this source code under
// the terms of the GPL-3.0 license that can be found in the LICENSE file.

#ifndef CHROME_BROWSER_UI_VIEWS_HELIUM_FULLSCREEN_WINDOW_CONTROLS_MAC_H_
#define CHROME_BROWSER_UI_VIEWS_HELIUM_FULLSCREEN_WINDOW_CONTROLS_MAC_H_

#import <Cocoa/Cocoa.h>

// Native traffic lights hosted in Helium's tab strip or toolbar. The system
// titlebar is restored when entering content fullscreen or leaving fullscreen.
@interface HeliumFullscreenWindowControls : NSView
- (instancetype)initWithWindow:(NSWindow*)window size:(NSSize)size;
- (void)hideTitlebarButtons;
- (void)setFullscreen:(BOOL)fullscreen;
- (void)restoreTitlebarButtons;
@end

#endif  // CHROME_BROWSER_UI_VIEWS_HELIUM_FULLSCREEN_WINDOW_CONTROLS_MAC_H_
