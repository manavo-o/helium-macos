// Copyright 2026 The Helium Authors
// You can use, redistribute, and/or modify this source code under
// the terms of the GPL-3.0 license that can be found in the LICENSE file.
#ifndef CHROME_BROWSER_UI_VIEWS_TABS_VERTICAL_ARC_NATIVE_UI_H_
#define CHROME_BROWSER_UI_VIEWS_TABS_VERTICAL_ARC_NATIVE_UI_H_
#include <memory>
#include <string>
#include <vector>
#include "base/functional/callback.h"
#include "ui/gfx/native_ui_types.h"
#include "ui/gfx/image/image_skia.h"
class BrowserWindowInterface;
namespace helium {
struct ArcNativeRow {
  std::u16string title, detail, action;
  std::string symbol;
  gfx::ImageSkia favicon;
  std::u16string input;
};
// Events: query, activate, force-search, selection, dismiss, destination.
using ArcNativeEvent = base::RepeatingCallback<void(int, const std::u16string&, int)>;
class ArcNativeCommandBar {
 public:
  virtual ~ArcNativeCommandBar() = default;
  virtual gfx::NativeView view() = 0;
  virtual void Focus() = 0;
  virtual void SetText(const std::u16string& text) = 0;
  virtual void Update(const std::vector<ArcNativeRow>& rows, int selected,
                      const std::u16string& destination, unsigned surface,
                      unsigned accent, unsigned on_accent, unsigned foreground,
                      unsigned secondary) = 0;
};
std::unique_ptr<ArcNativeCommandBar> CreateArcNativeCommandBar(ArcNativeEvent event);
void ShowArcAppearance(BrowserWindowInterface* browser);
}  // namespace helium
#endif
