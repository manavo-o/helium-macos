// Copyright 2026 The Helium Authors
// You can use, redistribute, and/or modify this source code under
// the terms of the GPL-3.0 license that can be found in the LICENSE file.

#include <algorithm>
#include <array>
#include <memory>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

#include "base/functional/bind.h"
#include "base/timer/timer.h"
#include "base/strings/string_split.h"
#include "chrome/browser/ui/helium/arc_appearance_prefs.h"
#include "chrome/browser/autocomplete/shortcuts_backend_factory.h"
#include "components/omnibox/browser/autocomplete_provider.h"
#include "components/omnibox/browser/shortcuts_backend.h"
#include "base/strings/escape.h"
#include "base/strings/string_util.h"
#include "base/strings/utf_string_conversions.h"
#include "chrome/app/chrome_command_ids.h"
#include "chrome/browser/autocomplete/autocomplete_classifier_factory.h"
#include "chrome/browser/autocomplete/chrome_autocomplete_provider_client.h"
#include "chrome/browser/autocomplete/chrome_autocomplete_scheme_classifier.h"
#include "chrome/browser/profiles/profile.h"
#include "chrome/browser/search_engines/template_url_service_factory.h"
#include "chrome/browser/ui/browser_commands.h"
#include "chrome/browser/ui/browser_window.h"
#include "chrome/browser/ui/browser_window/public/browser_window_interface.h"
#include "chrome/browser/ui/browser_window/public/global_browser_collection.h"
#include "chrome/browser/ui/helium/arc_command_bar.h"
#include "chrome/browser/ui/helium/arc_question_routing.h"
#include "chrome/browser/ui/navigator/browser_navigator.h"
#include "chrome/browser/ui/navigator/browser_navigator_params.h"
#include "chrome/browser/ui/tabs/tab_strip_model.h"
#include "chrome/browser/ui/views/frame/browser_view.h"
#include "chrome/browser/ui/views/frame/themed_background.h"
#include "chrome/browser/ui/views/frame/multi_contents_view.h"
#include "chrome/common/pref_names.h"
#include "components/omnibox/browser/autocomplete_classifier.h"
#include "components/omnibox/browser/autocomplete_controller.h"
#include "components/omnibox/browser/autocomplete_controller_config.h"
#include "components/omnibox/browser/autocomplete_input.h"
#include "components/omnibox/browser/autocomplete_match.h"
#include "components/omnibox/browser/autocomplete_result.h"
#include "components/prefs/pref_service.h"
#include "components/search_engines/template_url.h"
#include "components/search_engines/template_url_service.h"
#include "components/vector_icons/vector_icons.h"
#include "content/public/browser/web_contents.h"
#include "third_party/metrics_proto/omnibox_event.pb.h"
#include "ui/base/metadata/metadata_header_macros.h"
#include "ui/base/metadata/metadata_impl_macros.h"
#include "ui/base/models/image_model.h"
#include "ui/base/page_transition_types.h"
#include "ui/base/window_open_disposition.h"
#include "ui/color/color_id.h"
#include "ui/color/color_provider.h"
#include "ui/events/keycodes/keyboard_codes.h"
#include "ui/gfx/color_utils.h"
#include "ui/gfx/geometry/rounded_corners_f.h"
#include "ui/views/background.h"
#include "ui/views/border.h"
#include "ui/views/controls/button/label_button.h"
#include "ui/views/controls/label.h"
#include "ui/views/controls/textfield/textfield.h"
#include "ui/views/controls/textfield/textfield_controller.h"
#include "ui/views/layout/box_layout.h"
#include "ui/views/view_tracker.h"
#include "ui/views/view_utils.h"
#include "ui/views/widget/widget.h"
#include "ui/views/widget/widget_observer.h"
#include "url/gurl.h"

#include "components/favicon/content/content_favicon_driver.h"
#include "ui/accessibility/ax_enums.mojom.h"
#include "ui/views/controls/native/native_view_host.h"
#include "chrome/browser/ui/views/tabs/vertical/arc_native_ui.h"
#include "ui/views/layout/flex_layout.h"
#include "ui/views/view_class_properties.h"

namespace {

constexpr int kBarWidth = 760;
constexpr int kRowHeight = 46;
constexpr int kCornerRadius = 12;
constexpr int kMaxResults = 12;
constexpr int kArcToggleSidebar = -1;

bool LooksLikeURL(std::u16string_view text, Profile* profile) {
  const AutocompleteInput input(std::u16string(text),
                                metrics::OmniboxEventProto::INVALID_SPEC,
                                ChromeAutocompleteSchemeClassifier(profile));
  return input.type() == metrics::OmniboxInputType::URL;
}

struct Command {
  std::u16string_view title;
  int id;
  std::u16string_view shortcut;
  const gfx::VectorIcon* icon;
};

const auto kCommands = std::to_array<Command>({
    {u"New window", IDC_NEW_WINDOW, u"⌘N", &vector_icons::kAdd2Icon},
    {u"New private window", IDC_NEW_INCOGNITO_WINDOW, u"⇧⌘N", &vector_icons::kVisibilityOffIcon},
    {u"Toggle sidebar", kArcToggleSidebar, u"⌘S", &vector_icons::kSettingsIcon},
    {u"Extensions", IDC_MANAGE_EXTENSIONS, u"", &vector_icons::kSettingsIcon},
    {u"History", IDC_SHOW_HISTORY, u"⌘Y", &vector_icons::kHistoryIcon},
    {u"Downloads", IDC_SHOW_DOWNLOADS, u"⇧⌘J", &vector_icons::kDownloadIcon},
    {u"Settings", IDC_OPTIONS, u"⌘,", &vector_icons::kSettingsIcon},
    {u"Bookmark this page", IDC_BOOKMARK_THIS_TAB, u"⌘D", &vector_icons::kStarOldIcon},
    {u"Reopen closed tab", IDC_RESTORE_TAB, u"⇧⌘T", &vector_icons::kHistoryIcon},
    {u"Find in page", IDC_FIND, u"⌘F", &vector_icons::kSearchIcon},
    {u"Reload page", IDC_RELOAD, u"⌘R", &vector_icons::kReloadCustomIcon},
    {u"Toggle fullscreen", IDC_FULLSCREEN, u"⌃⌘F", &vector_icons::kOpenInNewFlippableIcon},
});

// The native SearchProvider retains its own URL/private-query eligibility
// checks. This client scopes the user's explicit suggestion choice to this UI
// and continues honoring a managed browser-wide prohibition.
class ArcSuggestionClient : public ChromeAutocompleteProviderClient {
 public:
  explicit ArcSuggestionClient(Profile* profile)
      : ChromeAutocompleteProviderClient(profile), profile_(profile) {}
  bool SearchSuggestEnabled() const override {
    const auto* settings = profile_->GetPrefs();
    return !profile_->IsOffTheRecord() && settings->GetBoolean(helium::kArcOnlineSuggestions) &&
        (!settings->IsManagedPreference(prefs::kSearchSuggestEnabled) ||
         ChromeAutocompleteProviderClient::SearchSuggestEnabled());
  }
 private:
  raw_ptr<Profile> profile_;
};

struct Result {
  enum class Kind { kInput, kTab, kCommand, kNavigation } kind;
  int command = 0;
  std::u16string title;
  std::u16string detail;
  std::u16string action;
  GURL url;
  base::WeakPtr<content::WebContents> tab;
  base::WeakPtr<BrowserWindowInterface> window;
  const gfx::VectorIcon* icon = &vector_icons::kSearchIcon;
  int score = 0;
  std::optional<AutocompleteMatch> match;

  bool SameIdentity(const Result& other) const {
    return kind == other.kind && command == other.command && url == other.url &&
           tab.get() == other.tab.get() && window.get() == other.window.get();
  }
};

class ArcCommandBarView : public views::View,
                          public views::TextfieldController,
                          public views::WidgetObserver,
                          public AutocompleteController::Observer {
  METADATA_HEADER(ArcCommandBarView, views::View)
 public:
  ArcCommandBarView(BrowserWindowInterface* browser, int width, int visible_rows, bool edit_current)
      : browser_(browser->GetWeakPtr()), edit_current_(edit_current),
        width_(width), visible_rows_(visible_rows) {
    SetLayoutManager(std::make_unique<views::BoxLayout>(
        views::BoxLayout::Orientation::kVertical));
    // The input model remains a Chromium Textfield for the existing routing
    // interface; all visible editing and layout are owned by SwiftUI/AppKit.
    textfield_ = AddChildView(std::make_unique<views::Textfield>());
    textfield_->SetVisible(false);
    textfield_->set_controller(this);
    AutocompleteControllerConfig config;
    config.provider_types = helium::ArcLocalAutocompleteProviders();
    config.disable_ml = true;
    config.show_iph_matches = false;
    autocomplete_ = std::make_unique<AutocompleteController>(
        std::make_unique<ChromeAutocompleteProviderClient>(browser_->GetProfile()), config);
    autocomplete_->AddObserver(this);
    AutocompleteControllerConfig search_config;
    search_config.provider_types = static_cast<int>(AutocompleteProvider::Type::kSearch);
    search_config.disable_ml = true;
    search_config.show_iph_matches = false;
    remote_ = std::make_unique<AutocompleteController>(
        std::make_unique<ArcSuggestionClient>(browser_->GetProfile()), search_config);
    remote_->AddObserver(this);
    auto* view = BrowserView::GetBrowserViewForBrowser(browser_.get());
    if (view && view->GetFocusManager()) {
      previous_focus_.SetView(view->GetFocusManager()->GetFocusedView());
    }
    native_ = helium::CreateArcNativeCommandBar(base::BindRepeating(
        &ArcCommandBarView::NativeEvent, base::Unretained(this)));
    native_host_ = AddChildView(std::make_unique<views::NativeViewHost>());
    native_host_->SetFocusBehavior(FocusBehavior::ALWAYS);
    if (edit_current_) {
      auto* current = browser_->GetTabStripModel()->GetActiveWebContents();
      if (current) {
        edit_target_ = current->GetWeakPtr();
        textfield_->SetText(base::UTF8ToUTF16(current->GetVisibleURL().spec()));
      }
    }
    UpdateResults();
  }
  ~ArcCommandBarView() override {
    if (parent_widget_) parent_widget_->RemoveObserver(this);
    search_timer_.Stop();
    remote_->RemoveObserver(this);
    remote_->Stop(AutocompleteStopReason::kClobbered);
    autocomplete_->RemoveObserver(this);
    autocomplete_->Stop(AutocompleteStopReason::kClobbered);
  }
  views::Textfield* textfield() { return textfield_; }
  // NativeViewHost creates its macOS wrapper when inserted into a Widget.
  void AttachNativeView() { native_host_->Attach(native_->view()); }
  void ObserveParent(views::Widget* parent) {
    parent_widget_ = parent;
    parent->AddObserver(this);
  }
  void OnWidgetBoundsChanged(views::Widget* widget, const gfx::Rect&) override {
    if (widget != parent_widget_ || !browser_) return;
    auto* view = BrowserView::GetBrowserViewForBrowser(browser_.get());
    if (!view || !GetWidget()) return;
    const auto page = view->GetBoundsInScreen();
    if (page.width() < 160 || page.height() < 180) { GetWidget()->Close(); return; }
    width_ = std::min(kBarWidth, page.width() - 48);
    visible_rows_ = std::clamp((page.height() - 180) / (kRowHeight + 4), 1, 5);
    const auto size = GetPreferredSize();
    native_host_->SetPreferredSize(size);
    GetWidget()->SetBounds(gfx::Rect(page.CenterPoint().x() - size.width() / 2,
        page.y() + std::clamp(page.height() * 3 / 10, 16,
            std::max(16, page.height() - size.height() - 16)), size.width(), size.height()));
  }
  bool editing_current() const { return edit_current_; }
  void FocusInput() { native_->Focus(); }
  void SeedAddress() {
    if (edit_current_) native_->SetText(std::u16string(textfield_->GetText()));
  }
  void SetInputForTesting(const std::u16string& text) { native_->SetText(text); }
  gfx::Size CalculatePreferredSize(const views::SizeBounds&) const override {
    return gfx::Size(width_, 20 + 56 + 1 + 8 +
        std::min(static_cast<int>(results_.size()), visible_rows_) * (kRowHeight + 4));
  }

  void ContentsChanged(views::Textfield*, const std::u16string& text) override {
    if (!browser_) { GetWidget()->Close(); return; }
    selection_explicit_ = false;
    selected_ = 0;
    updating_input_ = true;
    search_timer_.Stop();
    remote_query_.clear();
    remote_->Stop(AutocompleteStopReason::kClobbered);
    if (text.empty()) {
      autocomplete_->Stop(AutocompleteStopReason::kClobbered);
    } else {
      AutocompleteInput input(text, metrics::OmniboxEventProto::INVALID_SPEC,
                              ChromeAutocompleteSchemeClassifier(browser_->GetProfile()));
      input.set_prevent_inline_autocomplete(true);
      autocomplete_->Start(input);
      if (!browser_->GetProfile()->IsOffTheRecord() &&
          browser_->GetProfile()->GetPrefs()->GetBoolean(helium::kArcOnlineSuggestions)) {
        search_timer_.Start(FROM_HERE, base::Milliseconds(120), base::BindOnce(
            &ArcCommandBarView::StartRemoteSuggestions, base::Unretained(this), text));
      }
    }
    updating_input_ = false;
    UpdateResults();
  }
  void StartRemoteSuggestions(const std::u16string& query) {
    if (closing_ || !browser_ || textfield_->GetText() != query) return;
    remote_query_ = query;
    AutocompleteInput input(query, metrics::OmniboxEventProto::INVALID_SPEC,
                            ChromeAutocompleteSchemeClassifier(browser_->GetProfile()));
    input.set_prevent_inline_autocomplete(true);
    remote_->Start(input);
    UpdateResults();
  }
  void OnResultChanged(AutocompleteController*, bool) override {
    if (!closing_ && !updating_input_) UpdateResults();
  }
  void OnWidgetDestroying(views::Widget* widget) override {
    if (widget == parent_widget_) {
      parent_widget_->RemoveObserver(this);
      parent_widget_ = nullptr;
      restore_focus_ = false;
      if (GetWidget() && !GetWidget()->IsClosed()) GetWidget()->Close();
      return;
    }
    closing_ = true;
    search_timer_.Stop();
    remote_->Stop(AutocompleteStopReason::kClobbered);
    widget->RemoveObserver(this);
    autocomplete_->Stop(AutocompleteStopReason::kClobbered);
    if (restore_focus_ && browser_) {
      if (previous_focus_.view() && previous_focus_.view()->IsDrawn())
        previous_focus_.view()->RequestFocus();
      else chrome::FocusToolbar(browser_.get());
    }
  }
  void OnWidgetActivationChanged(views::Widget* widget, bool active) override {
    if (widget == parent_widget_) return;
    if (!active && !widget->IsClosed()) {
      restore_focus_ = false;
      widget->Close();
    }
  }
  bool OnKeyPressed(const ui::KeyEvent& event) override {
    if (event.key_code() == ui::VKEY_ESCAPE) { GetWidget()->Close(); return true; }
    if (event.key_code() == ui::VKEY_RETURN && event.IsCommandDown()) {
      Submit(true); return true;
    }
    return views::View::OnKeyPressed(event);
  }
  bool HandleKeyEvent(views::Textfield* sender, const ui::KeyEvent& event) override {
    if (event.type() != ui::EventType::kKeyPressed || sender->IsIMEComposing()) return false;
    if (event.key_code() == ui::VKEY_ESCAPE) { GetWidget()->Close(); return true; }
    if (event.key_code() == ui::VKEY_DOWN || event.key_code() == ui::VKEY_UP) {
      if (results_.empty()) return true;
      selected_ = (selected_ + (event.key_code() == ui::VKEY_DOWN ? 1 : results_.size() - 1)) % results_.size();
      UpdateAppearance();
      return true;
    }
    if (event.key_code() == ui::VKEY_RETURN) {
      if (event.IsCommandDown()) Submit(true);
      else if (!results_.empty()) ActivateResult(selected_);
      else Submit(false);
      return true;
    }
    return false;
  }
  void OnThemeChanged() override {
    views::View::OnThemeChanged();
    if (!GetColorProvider() || !textfield_) return;
    auto* browser_view = browser_ ? BrowserView::GetBrowserViewForBrowser(browser_.get()) : nullptr;
    const SkColor base = browser_view ? ThemedBackground::GetBackgroundColor(
        browser_view, browser_view, ThemedBackground::kFrameTheme)
        .value_or(GetColorProvider()->GetColor(ui::kColorFrameActive))
        : GetColorProvider()->GetColor(ui::kColorFrameActive);
    const bool dark = color_utils::IsDark(GetColorProvider()->GetColor(ui::kColorSysSurface));
    surface_ = color_utils::GetResultingPaintColor(
        dark ? SkColorSetARGB(240, 20, 22, 25) : SkColorSetARGB(245, 255, 255, 255), base);
    SetBackground(nullptr);
    UpdateAppearance();
  }
 private:
  void NativeEvent(int kind, const std::u16string& text, int index) {
    if (!browser_) { GetWidget()->Close(); return; }
    if (kind == 1) {
      if (textfield_->GetText() != text) {
        textfield_->SetText(text);
        ContentsChanged(textfield_, text);
      }
    }
    if (kind == 7) { ActivateResult(index); }
    else if (kind == 2) {
      if (text.empty() && index >= 0 && index < static_cast<int>(results_.size()) &&
          results_[index].kind == Result::Kind::kCommand) return;
      ActivateResult(index);
    } else if (kind == 3) Submit(true);
    else if (kind == 4 && index >= 0 && index < static_cast<int>(results_.size())) {
      selection_explicit_ = true; selected_ = index; UpdateAppearance();
    } else if (kind == 5) GetWidget()->Close();
    else if (kind == 6) ToggleDestination();
  }
  bool AskChatGPT() const {
    return browser_ && helium::ResolveArcFreeText(textfield_->GetText(), false, explicit_chatgpt_,
        browser_->GetProfile()->GetPrefs()->GetBoolean(prefs::kHeliumArcQuestionRouting),
        browser_->GetProfile()->IsOffTheRecord()) == helium::ArcDestination::kChatGPT;
  }
  void ToggleDestination() {
    explicit_chatgpt_ = !AskChatGPT();
    UpdateResults();
    if (native_) native_->Focus();
  }
  void UpdateResults() {
    if (!browser_) return;
    std::optional<Result> previous;
    const std::u16string query = base::ToLowerASCII(std::u16string(
        base::TrimWhitespace(textfield_->GetText(), base::TRIM_ALL)));
    if (selection_explicit_ && query == previous_query_ && selected_ >= 0 && selected_ < static_cast<int>(results_.size()))
      previous = results_[selected_];
    previous_query_ = query;
    results_.clear();
    const bool question = AskChatGPT();
    const auto tokens = base::SplitString(query, u" ", base::TRIM_WHITESPACE, base::SPLIT_WANT_NONEMPTY);
    auto command_score = [&](std::u16string_view title) {
      const auto name = base::ToLowerASCII(title);
      if (query.empty()) return 100;
      if (name == query) return 2200;
      if (query.size() >= 3 && name.starts_with(query)) return 2000;
      return name.find(query) != std::u16string::npos ? 600 : 0;
    };
    for (const auto& command : kCommands) {
      const int score = command_score(command.title);
      if (score && (command.id == kArcToggleSidebar || chrome::IsCommandEnabled(browser_.get(), command.id))) {
        results_.push_back({Result::Kind::kCommand, command.id, std::u16string(command.title),
            u"", std::u16string(command.shortcut), {}, {}, {}, command.icon, score});
      }
    }
    if (!query.empty()) {
      const bool url = LooksLikeURL(textfield_->GetText(), browser_->GetProfile());
      results_.push_back({Result::Kind::kInput, 0, std::u16string(textfield_->GetText()),
          u"", url ? u"Open URL" : question ? u"Ask ChatGPT" : u"Search", {}, {}, {},
          &vector_icons::kSearchIcon, url ? 2100 : question ? 2100 : 1100});
    }
    std::vector<Result> tabs;
    GlobalBrowserCollection::GetInstance()->ForEach([&](BrowserWindowInterface* window) {
      if (window->GetProfile() != browser_->GetProfile()) return true;
      auto* strip = window->GetTabStripModel();
      for (int i = 0; i < strip->count(); ++i) {
        auto* contents = strip->GetWebContentsAt(i);
        if (helium::IsArcHome(contents)) continue;
        const auto title = contents->GetTitle();
        const auto url = contents->GetVisibleURL();
        const auto title_key = base::ToLowerASCII(title);
        const auto url_key = base::ToLowerASCII(base::UTF8ToUTF16(url.spec()));
        const auto host = base::UTF8ToUTF16(url.host());
        if (!std::ranges::all_of(tokens, [&](const auto& token) {
              return title_key.find(token) != std::u16string::npos || url_key.find(token) != std::u16string::npos;
            })) continue;
        int score = query.empty() ? 1600 : title_key == query || host == query ? 1800
            : host.starts_with(query) ? 1700 : title_key.starts_with(query) ? 1600 : 1000;
        tabs.push_back({Result::Kind::kTab, 0, title.empty() ? host : title,
            host, u"Switch to Tab", url, contents->GetWeakPtr(), window->GetWeakPtr(),
            &vector_icons::kGlobeIcon, score});
      }
      return true;
    });
    std::stable_sort(tabs.begin(), tabs.end(), [](const Result& a, const Result& b) {
      return a.score != b.score ? a.score > b.score
          : a.tab->GetLastActiveTimeTicks() > b.tab->GetLastActiveTimeTicks();
    });
    for (const auto& tab : tabs) {
      if (query.empty() && results_.size() >= 5 + kCommands.size()) break;
      results_.push_back(tab);
    }
    if (!query.empty()) {
      auto add_matches = [&](const AutocompleteResult& matches, bool remote) {
        for (const auto& match : matches) {
          if (!match.destination_url.is_valid()) continue;
          const bool search = AutocompleteMatch::IsSearchType(match.type);
          if (search && (!remote || base::ToLowerASCII(match.fill_into_edit) == query)) continue;
          if (std::ranges::any_of(results_, [&](const Result& r) { return r.url == match.destination_url; })) continue;
          Result result{Result::Kind::kNavigation, 0,
              search ? match.fill_into_edit : match.description.empty() ? match.contents : match.description,
              search ? u"" : base::UTF8ToUTF16(match.destination_url.spec()),
              search ? u"" : u"Open", match.destination_url, {}, {},
              search ? &vector_icons::kSearchIcon : &vector_icons::kGlobeIcon,
              search ? std::min(1050, match.relevance) : match.allowed_to_be_default_match
                  ? std::max(1500, match.relevance) : std::min(1090, match.relevance)};
          result.match = match;
          results_.push_back(std::move(result));
        }
      };
      add_matches(autocomplete_->result(), false);
      if (remote_query_ == textfield_->GetText()) add_matches(remote_->result(), true);
    }
    if (query.empty() || query == u"edit appearance" || query == u"appearance" || query == u"theme") {
      results_.push_back({Result::Kind::kCommand, IDC_SHOW_CUSTOMIZE_CHROME_SIDE_PANEL,
          u"Edit appearance", u"", u"Customize", {}, {}, {}, &vector_icons::kSettingsIcon,
          query.empty() ? 90 : 2200});
    }
    std::stable_sort(results_.begin(), results_.end(), [](const Result& a, const Result& b) { return a.score > b.score; });
    if (results_.size() > (query.empty() ? 5u : kMaxResults)) results_.resize(query.empty() ? 5u : kMaxResults);
    selected_ = 0;
    for (size_t i = 0; previous && i < results_.size(); ++i) {
      if (results_[i].SameIdentity(*previous)) { selected_ = i; break; }
    }
    if (results_.size() > kMaxResults) results_.resize(kMaxResults);
    selected_ = std::min(selected_, std::max(0, static_cast<int>(results_.size()) - 1));
    UpdateAppearance();
    if (GetWidget()) {
      const auto size = GetPreferredSize();
      if (GetWidget()->GetWindowBoundsInScreen().size() != size) GetWidget()->SetSize(size);
    }
  }
  void UpdateAppearance() {
    if (native_ && GetColorProvider()) {
      std::vector<helium::ArcNativeRow> values;
      for (const auto& result : results_) {
        std::string symbol = "globe";
        if (result.kind == Result::Kind::kInput) symbol = AskChatGPT() ? "bubble.left" : "magnifyingglass";
        if (result.kind == Result::Kind::kCommand) {
          switch (result.command) {
            case IDC_NEW_WINDOW: symbol = "plus.rectangle"; break;
            case IDC_NEW_INCOGNITO_WINDOW: symbol = "eye.slash"; break;
            case IDC_SHOW_HISTORY: case IDC_RESTORE_TAB: symbol = "clock.arrow.circlepath"; break;
            case IDC_SHOW_DOWNLOADS: symbol = "arrow.down.circle"; break;
            case IDC_BOOKMARK_THIS_TAB: symbol = "star"; break;
            case IDC_FIND: symbol = "magnifyingglass"; break;
            case IDC_RELOAD: symbol = "arrow.clockwise"; break;
            case IDC_FULLSCREEN: symbol = "arrow.up.left.and.arrow.down.right"; break;
            case IDC_SHOW_CUSTOMIZE_CHROME_SIDE_PANEL: symbol = "paintpalette"; break;
            default: symbol = "gearshape";
          }
        }
        gfx::ImageSkia favicon;
        if (result.tab) {
          auto* driver = favicon::ContentFaviconDriver::FromWebContents(result.tab.get());
          if (driver && !driver->GetFavicon().IsEmpty()) favicon = driver->GetFavicon().AsImageSkia();
        }
        values.push_back({result.title, result.detail, result.action, symbol, favicon,
            (result.kind == Result::Kind::kTab ||
             (result.kind == Result::Kind::kNavigation && result.action == u"Open"))
                ? base::UTF8ToUTF16(result.url.spec()) : result.title});
      }
      auto color = [&](ui::ColorId id) { return GetColorProvider()->GetColor(id); };
      native_->Update(values, selected_, AskChatGPT() ? u"Ask ChatGPT" : u"Search", surface_,
          color(ui::kColorSysPrimary), color(ui::kColorSysOnPrimary),
          color(ui::kColorSysOnSurface), color(ui::kColorSysOnSurfaceVariant));
      if (native_host_) native_host_->SetPreferredSize(GetPreferredSize());
    }
  }
  void ActivateResult(int index) {
    if (!browser_ || index < 0 || index >= static_cast<int>(results_.size())) return;
    const Result result = results_[index];
    if (result.kind == Result::Kind::kInput) { Submit(false); return; }
    if (result.kind == Result::Kind::kTab) {
      if (!result.window || !result.tab) { UpdateResults(); return; }
      auto* tabs = result.window->GetTabStripModel();
      const int tab_index = tabs->GetIndexOfWebContents(result.tab.get());
      if (tab_index == TabStripModel::kNoTab) { UpdateResults(); return; }
      restore_focus_ = false;
      GetWidget()->Close();
      tabs->ActivateTabAt(tab_index);
      result.window->GetWindow()->Activate();
      return;
    }
    if (result.match && !browser_->GetProfile()->IsOffTheRecord()) {
      auto backend = ShortcutsBackendFactory::GetForProfile(browser_->GetProfile());
      if (backend && backend->initialized()) backend->AddOrUpdateShortcut(
          std::u16string(textfield_->GetText()), *result.match);
    }
    restore_focus_ = false;
    GetWidget()->Close();
    if (result.kind == Result::Kind::kCommand && result.command == kArcToggleSidebar) {
      if (auto* view = BrowserView::GetBrowserViewForBrowser(browser_.get())) view->ToggleZenModeSideChrome();
    } else if (result.kind == Result::Kind::kCommand) chrome::ExecuteCommand(browser_.get(), result.command);
    else NavigateTo(result.url);
  }
  void NavigateTo(const GURL& url) {
    if (!browser_ || !url.is_valid()) return;
    NavigateParams params(browser_.get(), url, ui::PAGE_TRANSITION_TYPED);
    if (edit_current_) {
      // Never redirect an edit into another tab if its original target closed.
      if (!edit_target_) return;
      const int index = browser_->GetTabStripModel()->GetIndexOfWebContents(edit_target_.get());
      if (index == TabStripModel::kNoTab) return;
      browser_->GetTabStripModel()->ActivateTabAt(index);
      params.disposition = WindowOpenDisposition::CURRENT_TAB;
    } else {
      params.disposition = helium::IsArcHome(
          browser_->GetTabStripModel()->GetActiveWebContents())
          ? WindowOpenDisposition::CURRENT_TAB
          : WindowOpenDisposition::NEW_FOREGROUND_TAB;
    }
    Navigate(&params);
  }
  void Submit(bool force_search) {
    if (!browser_) return;
    const std::u16string text(base::TrimWhitespace(textfield_->GetText(), base::TRIM_ALL));
    if (text.empty()) return;
    GURL destination;
    bool ask_chatgpt = false;
    if (force_search) {
      auto* service = TemplateURLServiceFactory::GetForProfile(browser_->GetProfile());
      if (service) destination = service->GenerateSearchURLForDefaultSearchProvider(text);
    } else {
      AutocompleteMatch match;
      AutocompleteClassifierFactory::GetForProfile(browser_->GetProfile())->Classify(
          text, false, true, metrics::OmniboxEventProto::INVALID_SPEC, &match, nullptr);
      ask_chatgpt = AutocompleteMatch::IsSearchType(match.type) && AskChatGPT();
      destination = ask_chatgpt
                        ? helium::ChatGPTWebsiteProvider::BuildSubmissionURL(text)
                        : match.destination_url;
    }
    if (!destination.is_valid()) return;
    if (ask_chatgpt) {
      // ChatGPT submits the encoded prompt once its page is ready. Keep the
      // source tab active and let the palette restore its previous focus.
      NavigateParams params(browser_.get(), destination,
                            ui::PAGE_TRANSITION_TYPED);
      params.disposition = WindowOpenDisposition::NEW_BACKGROUND_TAB;
      GetWidget()->Close();
      Navigate(&params);
      return;
    }
    restore_focus_ = false;
    GetWidget()->Close();
    NavigateTo(destination);
  }
  std::unique_ptr<helium::ArcNativeCommandBar> native_;
  raw_ptr<views::NativeViewHost> native_host_ = nullptr;
  base::WeakPtr<BrowserWindowInterface> browser_;
  const bool edit_current_;
  base::WeakPtr<content::WebContents> edit_target_;
  int width_;
  int visible_rows_;
  raw_ptr<views::Widget> parent_widget_ = nullptr;
  SkColor surface_ = SK_ColorTRANSPARENT;
  raw_ptr<views::Textfield> textfield_ = nullptr;
  std::vector<Result> results_;
  std::u16string previous_query_;
  int selected_ = 0;
  std::optional<bool> explicit_chatgpt_;
  std::unique_ptr<AutocompleteController> autocomplete_;
  std::unique_ptr<AutocompleteController> remote_;
  base::OneShotTimer search_timer_;
  std::u16string remote_query_;
  bool closing_ = false;
  bool updating_input_ = false;
  bool selection_explicit_ = false;
  views::ViewTracker previous_focus_;
  bool restore_focus_ = true;
};
BEGIN_METADATA(ArcCommandBarView)
END_METADATA
}  // namespace

namespace helium {
void SetArcCommandBarInputForTesting(BrowserWindowInterface* browser, const std::u16string& text) {
  auto* view = BrowserView::GetBrowserViewForBrowser(browser);
  if (!view || !view->GetWidget()) return;
  for (views::Widget* widget : views::Widget::GetAllOwnedWidgets(view->GetWidget()->GetNativeView())) {
    if (widget->GetName() == "ArcCommandBar" && !widget->IsClosed()) {
      if (auto* bar = views::AsViewClass<ArcCommandBarView>(widget->GetContentsView())) bar->SetInputForTesting(text);
    }
  }
}
bool IsArcHome(content::WebContents* contents) {
  if (!contents) return false;
  const auto& url = contents->GetVisibleURL();
  return url.SchemeIs("chrome") &&
      (url.host() == "newtab" || url.host() == "new-tab-page" || url.host() == "new-tab-page-third-party");
}
bool ShowArcCommandBar(BrowserWindowInterface* browser, bool edit_current) {
  auto* view = BrowserView::GetBrowserViewForBrowser(browser);
  auto* parent = view ? view->GetWidget() : nullptr;
  if (!parent || !view->multi_contents_view()) return false;
  for (views::Widget* widget : views::Widget::GetAllOwnedWidgets(parent->GetNativeView())) {
    if (widget->GetName() == "ArcCommandBar" && !widget->IsClosed()) {
      auto* bar = views::AsViewClass<ArcCommandBarView>(widget->GetContentsView());
      if (bar && bar->editing_current() == edit_current) {
        widget->Activate();
        bar->FocusInput();
        return true;
      }
      widget->Close();
    }
  }
  const auto page = view->GetBoundsInScreen();
  if (page.width() < 160 || page.height() < 180) return false;
  const int width = std::min(kBarWidth, page.width() - 48);
  const int rows = std::clamp((page.height() - 180) / (kRowHeight + 4), 1, 5);
  auto contents = std::make_unique<ArcCommandBarView>(browser, width, rows, edit_current);
  auto* bar = contents.get();
  const auto size = contents->GetPreferredSize();
  views::Widget::InitParams params(views::Widget::InitParams::NATIVE_WIDGET_OWNS_WIDGET,
                                  views::Widget::InitParams::TYPE_POPUP);
  params.parent = parent->GetNativeView();
  params.opacity = views::Widget::InitParams::WindowOpacity::kTranslucent;
  params.shadow_type = views::Widget::InitParams::ShadowType::kDrop;
  params.rounded_corners = gfx::RoundedCornersF(kCornerRadius);
  params.activatable = views::Widget::InitParams::Activatable::kYes;
  params.name = "ArcCommandBar";
  params.bounds = gfx::Rect(page.CenterPoint().x() - size.width() / 2,
      page.y() + std::clamp(page.height() * 3 / 10, 16,
          std::max(16, page.height() - size.height() - 16)), size.width(), size.height());
  auto* widget = new views::Widget();
  widget->Init(std::move(params));
  widget->SetContentsView(std::move(contents));
  bar->AttachNativeView();
  widget->AddObserver(bar);
  bar->ObserveParent(parent);
  widget->Show();
  widget->Activate();
  bar->FocusInput();
  bar->SeedAddress();
  return true;
}
}  // namespace helium
