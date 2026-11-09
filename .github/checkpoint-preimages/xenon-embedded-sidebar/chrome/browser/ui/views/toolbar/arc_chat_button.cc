// Copyright 2026 The Helium Authors
// You can use, redistribute, and/or modify this source code under
// the terms of the GPL-3.0 license that can be found in the LICENSE file.

#include "base/timer/timer.h"
#include "chrome/browser/ui/views/side_panel/side_panel_coordinator.h"
#include "base/task/single_thread_task_runner.h"
#include "base/memory/weak_ptr.h"
#include "chrome/browser/ui/views/toolbar/arc_chat_button.h"

#include "base/functional/bind.h"
#include "base/scoped_observation.h"
#include "chrome/browser/profiles/profile.h"
#include "chrome/browser/ui/browser_window/public/browser_window_interface.h"
#include "chrome/browser/ui/extensions/extensions_toolbar_view_model.h"
#include "chrome/browser/ui/navigator/browser_navigator.h"
#include "chrome/browser/ui/navigator/browser_navigator_params.h"
#include "chrome/browser/ui/side_panel/side_panel_entry_key.h"
#include "chrome/browser/ui/side_panel/side_panel_ui.h"
#include "chrome/browser/ui/toolbar/toolbar_action_view_model.h"
#include "chrome/browser/ui/views/extensions/extensions_toolbar_desktop.h"
#include "chrome/browser/ui/views/frame/browser_view.h"
#include "chrome/browser/ui/views/side_panel/side_panel.h"
#include "chrome/common/pref_names.h"
#include "components/prefs/pref_member.h"
#include "components/vector_icons/vector_icons.h"
#include "extensions/browser/extension_registry.h"
#include "extensions/browser/extension_registry_observer.h"
#include "extensions/browser/extension_util.h"
#include "extensions/common/extension.h"
#include "ui/base/metadata/metadata_impl_macros.h"
#include "ui/base/models/image_model.h"
#include "ui/base/page_transition_types.h"
#include "ui/base/window_open_disposition.h"
#include "ui/color/color_id.h"
#include "ui/views/accessibility/view_accessibility.h"
#include "ui/views/bubble/bubble_dialog_delegate_view.h"
#include "ui/views/controls/button/md_text_button.h"
#include "ui/views/controls/label.h"
#include "ui/views/layout/box_layout.h"
#include "ui/views/view_observer.h"
#include "ui/views/widget/widget.h"

namespace {

// Verified from the installed official extension and its marketplace listing.
constexpr char kChatExtensionId[] = "hehggadaopoacecdllhhajmbjkdcmajg";

class ArcChatStatusBubble : public views::View {
  METADATA_HEADER(ArcChatStatusBubble, views::View)

 public:
  ArcChatStatusBubble(BrowserWindowInterface* browser, std::u16string status)
      : browser_(browser) {
    SetLayoutManager(std::make_unique<views::BoxLayout>(
        views::BoxLayout::Orientation::kVertical, gfx::Insets(), 12));
    auto* label = AddChildView(std::make_unique<views::Label>(status));
    label->SetMultiLine(true);
    label->SetHorizontalAlignment(gfx::ALIGN_LEFT);
    label->SetPreferredSize(gfx::Size(320, 0));
    label->SizeToFit(320);
    AddChildView(std::make_unique<views::MdTextButton>(
        base::BindRepeating(
            &ArcChatStatusBubble::Open, base::Unretained(this),
            GURL("chrome://extensions/?id=" + std::string(kChatExtensionId))),
        u"Manage ChatGPT extension"));
    AddChildView(std::make_unique<views::MdTextButton>(
        base::BindRepeating(&ArcChatStatusBubble::Open, base::Unretained(this),
                            GURL("https://chatgpt.com/")),
        u"Open ChatGPT website"));
  }

 private:
  void Open(const GURL& url) {
    NavigateParams params(browser_, url, ui::PAGE_TRANSITION_LINK);
    params.disposition = WindowOpenDisposition::NEW_FOREGROUND_TAB;
    GetWidget()->Close();
    Navigate(&params);
  }
  raw_ptr<BrowserWindowInterface> browser_;
};

BEGIN_METADATA(ArcChatStatusBubble)
END_METADATA

class ArcChatButton : public views::MdTextButton,
                      public extensions::ExtensionRegistryObserver {
  METADATA_HEADER(ArcChatButton, views::MdTextButton)

 public:
  ArcChatButton(BrowserWindowInterface* browser,
                ExtensionsToolbarDesktop* extensions)
      : MdTextButton(base::BindRepeating(&ArcChatButton::Activate,
                                         base::Unretained(this)),
                     u"Chat"),
        browser_(browser),
        extensions_(extensions) {
    SetCornerRadius(10);
    SetCustomPadding(gfx::Insets::VH(4, 8));
    SetImageModel(views::Button::STATE_NORMAL,
                  ui::ImageModel::FromVectorIcon(vector_icons::kChatIcon,
                                                 ui::kColorSysPrimary, 18));
    SetFocusBehavior(FocusBehavior::ALWAYS);
    GetViewAccessibility().SetName(u"Open ChatGPT extension side panel");
    show_button_.Init(
        prefs::kHeliumArcChatButton, browser_->GetProfile()->GetPrefs(),
        base::BindRepeating(&ArcChatButton::Update, base::Unretained(this)));
    registry_observation_.Observe(
        extensions::ExtensionRegistry::Get(browser_->GetProfile()));
    auto* view = BrowserView::GetBrowserViewForBrowser(browser_);
    if (view && view->side_panel()) {
      panel_observer_.observation.Observe(view->side_panel());
    }
    if (auto* panel = SidePanelUI::From(browser_)) {
      shown_subscription_ = panel->RegisterSidePanelShown(
          base::BindRepeating(&ArcChatButton::PanelShown, base::Unretained(this)));
    }
    Update();
  }

  void OnExtensionLoaded(content::BrowserContext*,
                         const extensions::Extension*) override {
    Update();
  }
  void OnExtensionReady(content::BrowserContext*,
                        const extensions::Extension*) override {
    Update();
  }
  void OnExtensionUnloaded(content::BrowserContext*,
                           const extensions::Extension*,
                           extensions::UnloadedExtensionReason) override {
    Update();
  }
  void PanelShown() {
    auto* panel = SidePanelCoordinator::From(browser_);
    if (panel && panel->IsEntryShowingOrLoading(SidePanelEntryKey(
        SidePanelEntryId::kExtension, kChatExtensionId))) {
      launch_pending_ = false;
      launch_timeout_.Stop();
      if (cancel_on_show_) {
        cancel_on_show_ = false;
        panel->Close();
      }
    }
    Update();
  }
  void PanelVisibilityChanged(bool visible) {
    // Visibility notifications arrive before the coordinator clears its key.
    // Read state after that transaction, and cancel safely on window teardown.
    base::SingleThreadTaskRunner::GetCurrentDefault()->PostTask(
        FROM_HERE, base::BindOnce(&ArcChatButton::Update, weak_factory_.GetWeakPtr()));
    if (!visible && restore_focus_ && GetVisible()) {
      restore_focus_ = false;
      RequestFocus();
    }
  }

 private:
  bool IsAllowed() const {
    return !browser_->GetProfile()->IsOffTheRecord() ||
           extensions::util::IsIncognitoEnabled(kChatExtensionId,
                                                browser_->GetProfile());
  }
  bool IsOpen() const {
    auto* panel = SidePanelCoordinator::From(browser_);
    return launch_pending_ || (panel && panel->IsEntryShowingOrLoading(SidePanelEntryKey(
                        SidePanelEntryId::kExtension, kChatExtensionId)));
  }
  void Update() {
    SetVisible(show_button_.GetValue());
    SetStyle(IsOpen() ? ui::ButtonStyle::kTonal : ui::ButtonStyle::kText);
    auto* registry = extensions::ExtensionRegistry::Get(browser_->GetProfile());
    const bool available =
        IsAllowed() &&
        registry->enabled_extensions().Contains(kChatExtensionId);
    const std::u16string name = IsOpen() ? u"Close Chat"
        : available ? u"Open Chat" : u"Set up the ChatGPT extension in this profile";
    SetTooltipText(name);
    GetViewAccessibility().SetName(name);
    if (IsOpen()) GetViewAccessibility().SetIsExpanded();
    else GetViewAccessibility().SetIsCollapsed();
  }
  void Activate() {
    if (IsAllowed() && IsOpen()) {
      launch_pending_ = false;
      launch_timeout_.Stop();
      auto* coordinator = SidePanelCoordinator::From(browser_);
      if (!coordinator || !coordinator->IsEntryShowingOrLoading(
          SidePanelEntryKey(SidePanelEntryId::kExtension, kChatExtensionId))) {
        // The extension's action callback has not requested its entry yet.
        // Cancel its eventual presentation without dispatching the action twice.
        cancel_on_show_ = true;
        Update();
        return;
      }
      cancel_on_show_ = false;
      restore_focus_ = true;
      SidePanelUI::From(browser_)->Toggle(
          SidePanelEntryKey(SidePanelEntryId::kExtension, kChatExtensionId),
          SidePanelOpenTrigger::kToolbarButton);
      Update();
      return;
    }
    auto* model = extensions_ ? extensions_->GetToolbarViewModel() : nullptr;
    if (IsAllowed() && model && model->GetActionModelForId(kChatExtensionId)) {
      restore_focus_ = true;
      cancel_on_show_ = false;
      launch_pending_ = true;
      launch_timeout_.Start(FROM_HERE, base::Seconds(5), base::BindOnce(
          [](base::WeakPtr<ArcChatButton> button) {
            if (!button) return;
            button->launch_pending_ = false;
            button->Update();
          }, weak_factory_.GetWeakPtr()));
      Update();
      // Same user-action dispatch as the extension's toolbar icon. Chromium
      // selects the active (focused split-pane) tab and checks permissions.
      model->ExecuteUserAction(
          kChatExtensionId,
          ToolbarActionViewModel::InvocationSource::kToolbarButton);
      return;
    }
    const std::u16string message =
        IsAllowed()
            ? u"Install or enable the official ChatGPT extension in this "
              u"browser "
              u"profile, then sign in through the extension."
            : u"ChatGPT is not allowed in private windows. You can change its "
              u"private-window permission in extension settings.";
    auto delegate = std::make_unique<views::BubbleDialogDelegate>(
        this, views::BubbleBorder::TOP_RIGHT);
    delegate->SetTitle(u"Set up Chat");
    delegate->SetButtons(static_cast<int>(ui::mojom::DialogButton::kNone));
    delegate->SetContentsView(
        std::make_unique<ArcChatStatusBubble>(browser_, message));
    views::BubbleDialogDelegate::CreateBubbleDeprecated(
        std::move(delegate),
        views::Widget::InitParams::NATIVE_WIDGET_OWNS_WIDGET)
        ->Show();
  }

  raw_ptr<BrowserWindowInterface> browser_;
  raw_ptr<ExtensionsToolbarDesktop> extensions_;
  BooleanPrefMember show_button_;
  bool restore_focus_ = false;
  bool launch_pending_ = false;
  bool cancel_on_show_ = false;
  base::OneShotTimer launch_timeout_;
  base::CallbackListSubscription shown_subscription_;
  base::ScopedObservation<extensions::ExtensionRegistry,
                          extensions::ExtensionRegistryObserver>
      registry_observation_{this};
  // Button already inherits ViewObserver through its animation delegate.
  // A separate observer avoids overriding the delegate's final deletion hook.
  struct PanelObserver : views::ViewObserver {
    explicit PanelObserver(ArcChatButton* button) : button(button) {}
    void OnViewVisibilityChanged(views::View*,
                                 views::View*,
                                 bool visible) override {
      button->PanelVisibilityChanged(visible);
    }
    void OnViewIsDeleting(views::View*) override { observation.Reset(); }
    raw_ptr<ArcChatButton> button;
    base::ScopedObservation<views::View, views::ViewObserver> observation{this};
  } panel_observer_{this};
  base::WeakPtrFactory<ArcChatButton> weak_factory_{this};
};

BEGIN_METADATA(ArcChatButton)
END_METADATA

}  // namespace

std::unique_ptr<views::View> CreateArcChatButton(
    BrowserWindowInterface* browser,
    ExtensionsToolbarDesktop* extensions) {
  return std::make_unique<ArcChatButton>(browser, extensions);
}
