// Copyright 2026 The Chromium Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#include "base/no_destructor.h"
#include "third_party/skia/include/core/SkBitmap.h"
#include "ui/gfx/image/image_skia.h"
#include "ui/gfx/image/image_skia_rep.h"
#include "chrome/browser/ui/views/frame/themed_background.h"

#include <optional>
#include <vector>
#include "base/strings/string_split.h"
#include "base/strings/string_number_conversions.h"
#include "cc/paint/paint_shader.h"
#include "chrome/browser/profiles/profile.h"
#include "chrome/common/pref_names.h"
#include "chrome/browser/ui/helium/arc_appearance_prefs.h"
#include "components/prefs/pref_service.h"
#include "ui/gfx/color_utils.h"

#include "chrome/browser/themes/theme_properties.h"
#include "chrome/browser/ui/color/chrome_color_id.h"
#include "chrome/browser/ui/views/frame/browser_view.h"
#include "chrome/browser/ui/views/frame/top_container_view.h"
#include "chrome/browser/ui/views/helium/native_frame_materials.h"
#include "chrome/browser/ui/views/tabs/tab_strip.h"
#include "chrome/grit/theme_resources.h"
#include "ui/base/theme_provider.h"
#include "ui/color/color_id.h"
#include "ui/color/color_provider.h"
#include "ui/gfx/canvas.h"

namespace {
std::vector<SkColor4f> ArcThemeColors(const BrowserView* browser_view) {
  std::vector<SkColor4f> colors;
  if (!browser_view || !browser_view->GetColorProvider()) return colors;
  auto* prefs = browser_view->GetProfile()->GetPrefs();
  const auto stops = base::SplitString(prefs->GetString(helium::kArcThemeColors),
      ",", base::TRIM_WHITESPACE, base::SPLIT_WANT_NONEMPTY);
  const SkColor surface = browser_view->GetColorProvider()->GetColor(ui::kColorSysSurface);
  const bool dark = color_utils::IsDark(surface);
  const int intensity = std::clamp(prefs->GetInteger(helium::kArcThemeIntensity), 10, 100);
  for (const auto& stop : stops) {
    if (colors.size() == 3) break;
    unsigned value = 0;
    if (stop.size() != 7 || stop[0] != '#' || !base::HexStringToUInt(stop.substr(1), &value)) continue;
    const SkColor color = color_utils::AlphaBlend(0xff000000 | value, surface,
        static_cast<SkAlpha>(intensity * (dark ? 1.1 : 1.9)));
    colors.push_back(SkColor4f::FromColor(color));
  }
  return colors;
}

bool WillPaintCustomImage(const views::View* view, int id) {
  const ui::ThemeProvider* const theme_provider = view->GetThemeProvider();
  return theme_provider->HasCustomImage(id);
}

bool IsFrameActive(const views::View* view) {
  return view->GetWidget() ? view->GetWidget()->ShouldPaintAsActive() : true;
}

std::pair<int, ui::ColorId> GetThemeChoiceInfo(
    ThemedBackground::ThemeChoice theme_choice,
    const views::View* view) {
  switch (theme_choice) {
    case ThemedBackground::ThemeChoice::kToolbarTheme:
      return {IDR_THEME_TOOLBAR, kColorToolbar};
    case ThemedBackground::ThemeChoice::kFrameTheme:
      if (IsFrameActive(view)) {
        return {IDR_THEME_FRAME, ui::kColorFrameActive};
      } else {
        return {IDR_THEME_FRAME_INACTIVE, ui::kColorFrameInactive};
      }
    default:
      NOTREACHED();
  }
}

}  // namespace

ThemedBackground::ThemedBackground(BrowserView* browser_view,
                                   ThemeChoice theme_choice)
    : browser_view_(browser_view), theme_choice_(theme_choice) {}

void ThemedBackground::Paint(gfx::Canvas* canvas, views::View* view) const {
  if (helium::ShouldUseNativeFrameMaterials(browser_view_) &&
      ArcThemeColors(browser_view_).empty()) {
    return;
  }

  PaintBackground(canvas, view, browser_view_, theme_choice_);
}

bool ThemedBackground::PaintThemeCustomImage(gfx::Canvas* canvas,
                                             const views::View* view,
                                             const BrowserView* browser_view,
                                             ThemeChoice theme_choice) {
  const auto colors = ArcThemeColors(browser_view);
  if (!colors.empty()) {
    gfx::Point origin;
    views::View::ConvertPointToTarget(view, browser_view, &origin);
    const SkPoint points[] = {
      SkPoint::Make(-origin.x(), -origin.y()),
      SkPoint::Make(browser_view->width() - origin.x(), browser_view->height() - origin.y())};
    cc::PaintFlags flags;
    if (colors.size() == 1) flags.setColor(colors[0].toSkColor());
    else flags.setShader(cc::PaintShader::MakeLinearGradient(points, colors.data(), nullptr,
        static_cast<int>(colors.size()), SkTileMode::kClamp));
    canvas->DrawRect(view->GetLocalBounds(), flags);
    if (browser_view->GetProfile()->GetPrefs()->GetBoolean(helium::kArcThemeGrain)) {
      // One static Retina texture, shared across paints. Keep the phase in
      // browser coordinates, just like the gradient, so adjacent views join.
      static const base::NoDestructor<gfx::ImageSkia> grain([] {
        SkBitmap bitmap;
        bitmap.allocN32Pixels(128, 128);
        for (int y = 0; y < 128; ++y) {
          for (int x = 0; x < 128; ++x) {
            uint32_t hash = static_cast<uint32_t>(x + y * 128) + 1u;
            hash = (hash ^ (hash >> 16)) * 0x7feb352du;
            hash = (hash ^ (hash >> 15)) * 0x846ca68bu;
            hash ^= hash >> 16;
            const int tone = (hash & 1u) ? 255 : 0;
            *bitmap.getAddr32(x, y) = SkPreMultiplyARGB(
                (hash >> 8) % 15u, tone, tone, tone);
          }
        }
        bitmap.setImmutable();
        return gfx::ImageSkia(gfx::ImageSkiaRep(bitmap, 2.0f));
      }());
      const int start_x = -((origin.x() % 64 + 64) % 64);
      const int start_y = -((origin.y() % 64 + 64) % 64);
      for (int y = start_y; y < view->height(); y += 64)
        for (int x = start_x; x < view->width(); x += 64)
          canvas->DrawImageInt(*grain, x, y);
    }
    return true;
  }
  int theme_resource_id = GetThemeChoiceInfo(theme_choice, view).first;

  if (!WillPaintCustomImage(view, theme_resource_id)) {
    return false;
  }

  const ui::ThemeProvider* const theme_provider = view->GetThemeProvider();
  PaintThemeAlignedImage(canvas, view, browser_view,
                         theme_provider->GetImageSkiaNamed(theme_resource_id));

  return true;
}

void ThemedBackground::PaintThemeAlignedImage(gfx::Canvas* canvas,
                                              const views::View* view,
                                              const BrowserView* browser_view,
                                              gfx::ImageSkia* image) {
  // Get the origin of this view and translate it to coordinate system of the
  // BrowserView.
  gfx::Point pos;
  views::View::ConvertPointToTarget(view, browser_view, &pos);

  // Add in the translation to account for positioning of the theme image
  // relative of the origin of BrowserView.
  pos.Offset(0, ThemeProperties::kFrameHeightAboveTabs);

  if (browser_view->theme_background_y_offset()) {
    pos.set_y(pos.y() + *browser_view->theme_background_y_offset());
  }

  // Make sure the the background will cover the entire clip path region.
  // TODO(crbug.com/41344902): Remove the clip code and just use local bounds
  // once the pixel canvas is enabled on all aura platforms.
  SkPath clip_path = view->clip_path();
  SkRect rect = clip_path.getBounds();
  const gfx::Rect bounds =
      !clip_path.isEmpty()
          ? gfx::Rect(rect.x(), rect.y(), rect.width(), rect.height())
          : view->GetLocalBounds();
  canvas->TileImageInt(*image, pos.x(), pos.y(), bounds.x(), bounds.y(),
                       bounds.width(), bounds.height(), 1.0f,
                       SkTileMode::kRepeat, SkTileMode::kMirror);
}

void ThemedBackground::PaintBackground(gfx::Canvas* canvas,
                                       const views::View* view,
                                       const BrowserView* browser_view,
                                       ThemeChoice theme_choice) {
  bool painted =
      PaintThemeCustomImage(canvas, view, browser_view, theme_choice);
  if (!painted) {
    canvas->DrawColor(view->GetColorProvider()->GetColor(
        GetThemeChoiceInfo(theme_choice, view).second));
  }
}

std::optional<SkColor> ThemedBackground::GetBackgroundColor(
    const views::View* view,
    const BrowserView* browser_view,
    ThemeChoice theme_choice) {
  const auto colors = ArcThemeColors(browser_view);
  if (!colors.empty()) return colors.front().toSkColor();
  std::pair<int, ui::ColorId> theme_choice_info =
      GetThemeChoiceInfo(theme_choice, view);
  if (helium::ShouldUseNativeFrameMaterials(browser_view)) {
    return std::nullopt;
  }

  const bool will_be_painted =
      WillPaintCustomImage(view, theme_choice_info.first);
  if (!will_be_painted) {
    return view->GetColorProvider()->GetColor(theme_choice_info.second);
  }

  return std::nullopt;
}
