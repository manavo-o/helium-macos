// Copyright 2026 The Helium Authors
// You can use, redistribute, and/or modify this source code under
// the terms of the GPL-3.0 license that can be found in the LICENSE file.

#import "chrome/browser/ui/views/helium/fullscreen_window_controls_mac.h"

#include <iterator>

#include "base/apple/foundation_util.h"
#import "components/remote_cocoa/app_shim/browser_native_widget_window_mac.h"

// Native titlebar buttons cache their presentation separately from NSView's
// display invalidation. Let AppKit refresh that state when group hover changes.
@interface NSButton (HeliumFullscreenWindowControlsHover)
- (void)mouseEnteredOrExited;
@end

@implementation HeliumFullscreenWindowControls {
  BrowserNativeWidgetWindow* __weak _browserWindow;
  NSDictionary<NSNumber*, NSNumber*>* _originalWindowButtonHiddenStates;
  BOOL _mouseInsideControls;
}

- (instancetype)initWithWindow:(NSWindow*)window size:(NSSize)size {
  self = [super initWithFrame:NSMakeRect(0, 0, size.width, size.height)];
  if (!self) {
    return nil;
  }
  _browserWindow = base::apple::ObjCCast<BrowserNativeWidgetWindow>(window);
  const NSWindowStyleMask style = window.styleMask & ~NSWindowStyleMaskFullScreen;
  const struct {
    NSWindowButton type;
    SEL action;
    bool enabled;
  } buttons[] = {
      {NSWindowCloseButton, @selector(performClose:),
       (style & NSWindowStyleMaskClosable) != 0},
      // Fullscreen windows cannot be minimized.
      {NSWindowMiniaturizeButton, @selector(performMiniaturize:), false},
      {NSWindowZoomButton, @selector(toggleFullScreen:),
       (style & NSWindowStyleMaskResizable) != 0},
  };

  NSMutableDictionary<NSNumber*, NSNumber*>* hiddenStates =
      [NSMutableDictionary dictionary];
  for (const auto& entry : buttons) {
    NSButton* original = [window standardWindowButton:entry.type];
    if (original) {
      hiddenStates[@(entry.type)] = @(original.hidden);
    }
  }
  _originalWindowButtonHiddenStates = hiddenStates;

  // Create ordinary window buttons even while AppKit's fullscreen titlebar
  // is hidden. Their visibility is controlled by Helium's toolbar instead.
  const bool rtl = window.windowTitlebarLayoutDirection ==
                   NSUserInterfaceLayoutDirectionRightToLeft;
  for (size_t i = 0; i < std::size(buttons); ++i) {
    const auto& entry = buttons[i];
    NSButton* button = [NSWindow standardWindowButton:entry.type
                                       forStyleMask:style];
    if (!button) {
      continue;
    }
    button.target = window;
    button.action = entry.action;
    button.enabled = entry.enabled;
    NSRect frame = button.frame;
    const CGFloat offset = (size.width - frame.size.width) * i / 2;
    frame.origin.x = rtl ? size.width - frame.size.width - offset : offset;
    frame.origin.y = (size.height - frame.size.height) / 2;
    button.frame = frame;
    [self addSubview:button];
  }

  // NSTrackingInVisibleRect follows layout changes without replacing the
  // tracking area and queuing enter/exit events for obsolete areas.
  NSTrackingArea* trackingArea = [[NSTrackingArea alloc]
      initWithRect:NSZeroRect
           options:NSTrackingMouseEnteredAndExited | NSTrackingActiveInKeyWindow |
                   NSTrackingInVisibleRect
             owner:self
          userInfo:nil];
  [self addTrackingArea:trackingArea];
  return self;
}

- (void)hideTitlebarButtons {
  [_browserWindow setAppKitFullscreenOverlaySuppressed:YES];
  // Look up current buttons because AppKit can recreate them.
  for (NSNumber* type in _originalWindowButtonHiddenStates) {
    NSButton* button = [_browserWindow standardWindowButton:
        static_cast<NSWindowButton>(type.unsignedIntegerValue)];
    button.hidden = YES;
  }
}

- (void)restoreTitlebarButtons {
  [_browserWindow setAppKitFullscreenOverlaySuppressed:NO];
  for (NSNumber* type in _originalWindowButtonHiddenStates) {
    NSButton* button = [_browserWindow standardWindowButton:
        static_cast<NSWindowButton>(type.unsignedIntegerValue)];
    // Restore the saved visibility while still fullscreen. Outside fullscreen,
    // show the buttons even if AppKit hid them during the entry transition.
    button.hidden = (button.window.styleMask & NSWindowStyleMaskFullScreen) &&
                    _originalWindowButtonHiddenStates[type].boolValue;
  }
}

- (void)setMouseInsideControls:(BOOL)inside {
  if (_mouseInsideControls == inside) {
    return;
  }
  _mouseInsideControls = inside;
  for (NSButton* button in self.subviews) {
    if ([button respondsToSelector:@selector(mouseEnteredOrExited)]) {
      [button mouseEnteredOrExited];
    }
    button.needsDisplay = YES;
  }
}

- (void)mouseEntered:(NSEvent*)event {
  [self setMouseInsideControls:YES];
}

- (void)mouseExited:(NSEvent*)event {
  [self setMouseInsideControls:NO];
}

- (void)setHidden:(BOOL)hidden {
  [super setHidden:hidden];
  if (hidden) {
    [self setMouseInsideControls:NO];
  }
}

// AppKit's standard window buttons ask their container for group hover state.
- (BOOL)_mouseInGroup:(id)sender {
  return _mouseInsideControls && self.window.isKeyWindow &&
         !self.hiddenOrHasHiddenAncestor && self.alphaValue > 0;
}

// Let clicks between the buttons reach the browser frame.
- (NSView*)hitTest:(NSPoint)point {
  NSView* view = [super hitTest:point];
  return view == self ? nil : view;
}

@end
