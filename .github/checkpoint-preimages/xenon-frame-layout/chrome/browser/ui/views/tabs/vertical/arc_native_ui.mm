// Copyright 2026 The Helium Authors
// You can use, redistribute, and/or modify this source code under
// the terms of the GPL-3.0 license that can be found in the LICENSE file.
#import <AppKit/AppKit.h>
#import <objc/runtime.h>
#include <algorithm>
#include "chrome/browser/ui/helium/arc_command_bar.h"
#include "chrome/browser/ui/tabs/tab_strip_model.h"
#include "content/public/browser/web_contents.h"
#include "ui/views/controls/native/native_view_host.h"
#include "chrome/browser/ui/views/tabs/vertical/arc_native_ui.h"
#include "chrome/browser/ui/views/tabs/vertical/arc_native_swift.h"
#include "base/strings/string_number_conversions.h"
#include "base/strings/sys_string_conversions.h"
#include "chrome/browser/browser_process.h"
#include "chrome/browser/profiles/profile.h"
#include "chrome/browser/themes/theme_service.h"
#include "chrome/browser/themes/theme_service_factory.h"
#include "chrome/browser/ui/browser_window/public/browser_window_interface.h"
#include "chrome/browser/ui/browser_window/public/global_browser_collection.h"
#include "chrome/browser/ui/views/frame/browser_view.h"
#include "chrome/common/pref_names.h"
#include "chrome/browser/ui/helium/arc_appearance_prefs.h"
#include "components/prefs/pref_service.h"
#include "ui/gfx/image/image_skia_util_mac.h"
#include "ui/views/widget/widget.h"
#include "ui/views/view_utils.h"
#include "ui/gfx/color_utils.h"
#include "chrome/browser/ui/views/frame/vertical_tab_strip_region_view.h"

#include "chrome/browser/ui/views/page_info/page_info_bubble_specification.h"
#include "chrome/browser/ui/views/page_info/page_info_bubble_view.h"
#include "content/public/browser/navigation_controller.h"
#include "content/public/browser/navigation_entry.h"
#include "ui/color/color_id.h"
#include "ui/color/color_provider.h"
#include "chrome/browser/ui/views/frame/themed_background.h"
#include "chrome/browser/ui/navigator/browser_navigator.h"
#include "chrome/browser/ui/navigator/browser_navigator_params.h"
#include "chrome/browser/ui/views/location_bar/location_bar_view.h"
#include "chrome/browser/ui/views/toolbar/toolbar_view.h"
namespace {
NSColor* NativeColor(unsigned color) {
  return [NSColor colorWithSRGBRed:((color >> 16) & 255) / 255.0
                           green:((color >> 8) & 255) / 255.0
                            blue:(color & 255) / 255.0 alpha:1];
}
class NativeCommandBar : public helium::ArcNativeCommandBar {
 public:
  explicit NativeCommandBar(helium::ArcNativeEvent event) {
    host_ = [[HeliumCommandBarHost alloc] initWithEvent:^(NSInteger kind, NSString* text, NSInteger index) {
      event.Run(static_cast<int>(kind), base::SysNSStringToUTF16(text), static_cast<int>(index));
    }];
  }
  ~NativeCommandBar() override { [host_ invalidate]; }
  gfx::NativeView view() override { return gfx::NativeView(host_.view); }
  void Focus() override { [host_ focus]; }
  void SetText(const std::u16string& text) override { [host_ setText:base::SysUTF16ToNSString(text)]; }
  void Update(const std::vector<helium::ArcNativeRow>& rows, int selected,
              const std::u16string& destination, unsigned surface, unsigned accent,
              unsigned on_accent, unsigned foreground, unsigned secondary) override {
    host_.view.appearance = [NSAppearance appearanceNamed:
        color_utils::IsDark(surface) ? NSAppearanceNameDarkAqua : NSAppearanceNameAqua];
    NSMutableArray* values = [NSMutableArray arrayWithCapacity:rows.size()];
    for (const auto& row : rows) {
      NSMutableDictionary* value = [@{
        @"title":base::SysUTF16ToNSString(row.title),
        @"detail":base::SysUTF16ToNSString(row.detail),
        @"action":base::SysUTF16ToNSString(row.action),
        @"symbol":base::SysUTF8ToNSString(row.symbol),
        @"input":base::SysUTF16ToNSString(row.input)} mutableCopy];
      if (!row.favicon.isNull()) value[@"favicon"] = gfx::NSImageFromImageSkia(row.favicon);
      [values addObject:value];
    }
    [host_ updateWithRows:values selected:selected destination:base::SysUTF16ToNSString(destination)
                  colors:@[NativeColor(surface), NativeColor(accent), NativeColor(on_accent),
                           NativeColor(foreground), NativeColor(secondary)]];
  }
 private:
  HeliumCommandBarHost* __strong host_;
};
void RefreshSpacing(views::View* view) {
  if (auto* region = views::AsViewClass<VerticalTabStripRegionView>(view))
    region->UpdateInteriorMargin();
  for (views::View* child : view->children()) RefreshSpacing(child);
  view->InvalidateLayout();
}
class NativeHomeSurface : public views::NativeViewHost {
 public:
  explicit NativeHomeSurface(BrowserWindowInterface* browser) {
    auto weak = browser->GetWeakPtr();
    host_ = [[XenonHomeHost alloc] initWithEvent:^{
      if (weak) helium::ShowArcCommandBar(weak.get());
    }];
    SetBackground(std::make_unique<ThemedBackground>(
        BrowserView::GetBrowserViewForBrowser(browser), ThemedBackground::kToolbarTheme));
  }
  ~NativeHomeSurface() override { [host_ invalidate]; }
  void OnThemeChanged() override {
    views::NativeViewHost::OnThemeChanged();
    if (GetColorProvider()) host_.view.appearance = [NSAppearance appearanceNamed:
        color_utils::IsDark(GetColorProvider()->GetColor(ui::kColorSysSurface))
            ? NSAppearanceNameDarkAqua : NSAppearanceNameAqua];
  }
  void AddedToWidget() override {
    views::NativeViewHost::AddedToWidget();
    Attach(gfx::NativeView(host_.view));
  }
 private:
  XenonHomeHost* __strong host_;
};
class NativeSidebarFooter : public views::NativeViewHost {
 public:
  explicit NativeSidebarFooter(BrowserWindowInterface* browser) {
    auto weak = browser->GetWeakPtr();
    host_ = [[XenonSidebarFooterHost alloc] initWithEvent:^(NSInteger action) {
      if (!weak) return;
      if (action == 0) { helium::ShowArcAppearance(weak.get()); return; }
      NavigateParams navigation(weak.get(), GURL(action == 1 ?
          "chrome://downloads/" : "chrome://settings/"), ui::PAGE_TRANSITION_LINK);
      navigation.disposition = WindowOpenDisposition::NEW_FOREGROUND_TAB;
      Navigate(&navigation);
    }];
    SetPreferredSize(gfx::Size(160, 36));
  }
  ~NativeSidebarFooter() override { [host_ invalidate]; }
  void OnThemeChanged() override {
    views::NativeViewHost::OnThemeChanged();
    if (GetColorProvider()) host_.view.appearance = [NSAppearance appearanceNamed:
        color_utils::IsDark(GetColorProvider()->GetColor(ui::kColorSysSurface))
            ? NSAppearanceNameDarkAqua : NSAppearanceNameAqua];
  }
  void AddedToWidget() override {
    views::NativeViewHost::AddedToWidget();
    Attach(gfx::NativeView(host_.view));
  }
 private:
  XenonSidebarFooterHost* __strong host_;
};
class NativeAddressDisplay : public views::NativeViewHost {
 public:
  explicit NativeAddressDisplay(BrowserWindowInterface* browser) {
    auto weak = browser->GetWeakPtr();
    host_ = [[XenonAddressHost alloc] initWithEvent:^(NSInteger action) {
      if (!weak) return;
      if (action == 1) {
        auto* contents = weak->GetTabStripModel()->GetActiveWebContents();
        auto* entry = contents ? contents->GetController().GetVisibleEntry() : nullptr;
        if (!entry || entry->IsInitialEntry() || !GetWidget()) return;
        auto specification = PageInfoBubbleSpecification::Builder(
            views::BubbleAnchor(this), GetWidget()->GetNativeWindow(),
            contents, entry->GetVirtualURL()).Build();
        auto* bubble = PageInfoBubbleView::CreatePageInfoBubble(std::move(specification));
        bubble->GetWidget()->Show();
        return;
      }
      if (weak) helium::ShowArcCommandBar(weak.get(),
          !helium::IsArcHome(weak->GetTabStripModel()->GetActiveWebContents()));
    }];
    SetPreferredSize(gfx::Size(280, 32));
    SetFocusBehavior(FocusBehavior::ALWAYS);
  }
  ~NativeAddressDisplay() override { [host_ invalidate]; }
  void OnThemeChanged() override {
    views::NativeViewHost::OnThemeChanged();
    if (GetColorProvider()) host_.view.appearance = [NSAppearance appearanceNamed:
        color_utils::IsDark(GetColorProvider()->GetColor(ui::kColorSysSurface))
            ? NSAppearanceNameDarkAqua : NSAppearanceNameAqua];
  }
  void AddedToWidget() override {
    views::NativeViewHost::AddedToWidget();
    Attach(gfx::NativeView(host_.view));
  }
  void Update(BrowserWindowInterface* browser) {
    auto* contents = browser ? browser->GetTabStripModel()->GetActiveWebContents() : nullptr;
    const bool home = !contents || helium::IsArcHome(contents);
    const GURL url = contents ? contents->GetVisibleURL() : GURL();
    [host_ updateWithTitle:home ? @"Search or Enter URL…" : base::SysUTF8ToNSString(
        url.host().empty() ? url.spec() : url.host())
        url:home ? @"" : base::SysUTF8ToNSString(url.spec())];
  }
 private:
  XenonAddressHost* __strong host_;
};
const char kAppearanceWindowKey = 0;
}  // namespace

@interface HeliumAppearanceWindow : NSWindowController
@property(nonatomic, strong) HeliumAppearanceHost* host;
@property(nonatomic, strong) id closeObserver;
@property(nonatomic, strong) id panelCloseObserver;
@end
@implementation HeliumAppearanceWindow
@synthesize host = _host;
@synthesize closeObserver = _closeObserver;
@synthesize panelCloseObserver = _panelCloseObserver;
- (void)dealloc {
  if (_closeObserver) [[NSNotificationCenter defaultCenter] removeObserver:_closeObserver];
  if (_panelCloseObserver) [[NSNotificationCenter defaultCenter] removeObserver:_panelCloseObserver];
}
@end

namespace helium {
std::unique_ptr<views::View> CreateArcHomeSurface(BrowserWindowInterface* browser) {
  return std::make_unique<NativeHomeSurface>(browser);
}
std::unique_ptr<views::View> CreateArcSidebarFooter(BrowserWindowInterface* browser) {
  return std::make_unique<NativeSidebarFooter>(browser);
}
std::unique_ptr<views::View> CreateArcAddressDisplay(BrowserWindowInterface* browser) {
  return std::make_unique<NativeAddressDisplay>(browser);
}
void UpdateArcAddressDisplay(views::View* view, BrowserWindowInterface* browser) {
  static_cast<NativeAddressDisplay*>(view)->Update(browser);
}
std::unique_ptr<ArcNativeCommandBar> CreateArcNativeCommandBar(ArcNativeEvent event) {
  return std::make_unique<NativeCommandBar>(std::move(event));
}
void ShowArcAppearance(BrowserWindowInterface* browser) {
  auto* view = BrowserView::GetBrowserViewForBrowser(browser);
  if (!view || !view->GetWidget()) return;
  NSWindow* parent = view->GetWidget()->GetNativeWindow().GetNativeNSWindow();
  if (HeliumAppearanceWindow* existing = objc_getAssociatedObject(parent, &kAppearanceWindowKey)) {
    [existing showWindow:nil];
    [existing.window makeKeyAndOrderFront:nil];
    return;
  }
  auto weak_browser = browser->GetWeakPtr();
  auto* prefs = browser->GetProfile()->GetPrefs();
  auto* local = g_browser_process->local_state();
  auto* theme = ThemeServiceFactory::GetForProfile(browser->GetProfile());
  NSPanel* panel = [[NSPanel alloc] initWithContentRect:NSMakeRect(0, 0, 480, 660)
      styleMask:NSWindowStyleMaskTitled | NSWindowStyleMaskClosable | NSWindowStyleMaskUtilityWindow
      backing:NSBackingStoreBuffered defer:NO];
  panel.title = @"Appearance";
  panel.releasedWhenClosed = NO;
  panel.animationBehavior = NSWindowAnimationBehaviorUtilityWindow;
  __weak NSPanel* weak_panel = panel;
  NSDictionary* values = @{
    @"colors":base::SysUTF8ToNSString(prefs->GetString(helium::kArcThemeColors)),
    @"intensity":@(prefs->GetInteger(helium::kArcThemeIntensity)).stringValue,
    @"suggestions":prefs->GetBoolean(helium::kArcOnlineSuggestions) ? @"true" : @"false",
    @"grain":prefs->GetBoolean(helium::kArcThemeGrain) ? @"true" : @"false",
    @"scheme":@(static_cast<int>(theme->GetBrowserColorScheme())).stringValue,
    @"density":@(local->GetInteger(prefs::kHeliumArcInterfaceDensity)).stringValue,
    @"tile":@(local->GetInteger(prefs::kHeliumArcPinnedTileSize)).stringValue};
  HeliumAppearanceHost* host = [[HeliumAppearanceHost alloc] initWithValues:values event:^(NSString* key, NSString* value) {
    if (!weak_browser) { [weak_panel close]; return; }
    auto* profile = weak_browser->GetProfile();
    auto* settings = profile->GetPrefs();
    auto* theme_service = ThemeServiceFactory::GetForProfile(profile);
    const std::string name = base::SysNSStringToUTF8(key);
    const std::string text = base::SysNSStringToUTF8(value);
    int number = 0;
    base::StringToInt(text, &number);
    if (name == "icloud") {
      NavigateParams navigation(weak_browser.get(),
          GURL("https://chromewebstore.google.com/detail/icloud-passwords/pejdijmoenmkgeppbflobdenhhabjlaj"),
          ui::PAGE_TRANSITION_LINK);
      navigation.disposition = WindowOpenDisposition::NEW_FOREGROUND_TAB;
      Navigate(&navigation);
      return;
    }
    if (name == "colors") {
      settings->SetString(helium::kArcThemeColors, text);
      unsigned color = 0;
      if (text.size() >= 7 && base::HexStringToUInt(text.substr(1, 6), &color))
        theme_service->SetUserColor(0xff000000 | color);
    } else if (name == "suggestions") settings->SetBoolean(helium::kArcOnlineSuggestions, text == "true");
    else if (name == "intensity") settings->SetInteger(helium::kArcThemeIntensity, std::clamp(number, 10, 100));
    else if (name == "grain") settings->SetBoolean(helium::kArcThemeGrain, text == "true");
    else if (name == "scheme") theme_service->SetBrowserColorScheme(static_cast<ThemeService::BrowserColorScheme>(std::clamp(number, 0, 2)));
    else if (name == "density") g_browser_process->local_state()->SetInteger(prefs::kHeliumArcInterfaceDensity, std::clamp(number, 0, 1));
    else if (name == "tile") g_browser_process->local_state()->SetInteger(prefs::kHeliumArcPinnedTileSize, std::clamp(number, 40, 72));
    else if (name == "reset") {
      for (const char* pref : {helium::kArcThemeColors, helium::kArcThemeIntensity, helium::kArcThemeGrain}) settings->ClearPref(pref);
      g_browser_process->local_state()->ClearPref(prefs::kHeliumArcInterfaceDensity);
      g_browser_process->local_state()->ClearPref(prefs::kHeliumArcPinnedTileSize);
      theme_service->SetBrowserColorScheme(ThemeService::BrowserColorScheme::kSystem);
      theme_service->SetUserColor(std::nullopt);
    } else if (name == "close") [weak_panel close];
    GlobalBrowserCollection::GetInstance()->ForEach([&](BrowserWindowInterface* other) {
      if (other->GetProfile() == profile || name == "density" || name == "tile") {
        auto* view = BrowserView::GetBrowserViewForBrowser(other);
        if (view && view->GetWidget()) {
          view->GetWidget()->ScheduleThemeChanged();
          if (name == "density" || name == "tile") RefreshSpacing(view);
          view->InvalidateLayout();
          view->SchedulePaint();
        }
      }
      return true;
    });
  }];
  panel.contentView = host.view;
  [panel setContentSize:host.view.fittingSize];
  auto* controller = [[HeliumAppearanceWindow alloc] initWithWindow:panel];
  controller.host = host;
  controller.closeObserver = [[NSNotificationCenter defaultCenter]
      addObserverForName:NSWindowWillCloseNotification object:parent queue:nil
      usingBlock:^(NSNotification*) { [weak_panel close]; }];
  __weak NSWindow* weak_parent = parent;
  controller.panelCloseObserver = [[NSNotificationCenter defaultCenter]
      addObserverForName:NSWindowWillCloseNotification object:panel queue:nil
      usingBlock:^(NSNotification*) {
        NSWindow* owner = weak_parent;
        if (owner) {
          [owner removeChildWindow:weak_panel];
          objc_setAssociatedObject(owner, &kAppearanceWindowKey, nil, OBJC_ASSOCIATION_RETAIN_NONATOMIC);
        }
      }];
  objc_setAssociatedObject(parent, &kAppearanceWindowKey, controller, OBJC_ASSOCIATION_RETAIN_NONATOMIC);
  [parent addChildWindow:panel ordered:NSWindowAbove];
  NSRect frame = panel.frame;
  frame.origin = NSMakePoint(NSMidX(parent.frame) - frame.size.width / 2,
                            NSMidY(parent.frame) - frame.size.height / 2);
  [panel setFrame:frame display:YES];
  [controller showWindow:nil];
  [panel makeKeyAndOrderFront:nil];
}
}  // namespace helium
