// Copyright 2026 The Helium Authors
// You can use, redistribute, and/or modify this source code under
// the terms of the GPL-3.0 license that can be found in the LICENSE file.

#include "chrome/browser/ui/helium/arc_command_bar.h"

#include <atomic>

#include "base/run_loop.h"
#include "chrome/browser/ui/helium/arc_appearance_prefs.h"
#include "components/prefs/pref_service.h"
#include "base/task/single_thread_task_runner.h"
#include "base/test/bind.h"
#include "chrome/app/chrome_command_ids.h"
#include "chrome/browser/search_engines/template_url_service_factory.h"
#include "chrome/browser/ui/browser.h"
#include "chrome/browser/profiles/profile.h"
#include "chrome/browser/ui/browser_commands.h"
#include "chrome/browser/ui/tabs/tab_strip_model.h"
#include "chrome/browser/ui/views/frame/browser_view.h"
#include "chrome/browser/ui/views/frame/multi_contents_view.h"
#include "chrome/test/base/in_process_browser_test.h"
#include "chrome/test/base/interactive_test_utils.h"
#include "chrome/test/base/search_test_utils.h"
#include "components/search_engines/template_url.h"
#include "components/search_engines/template_url_data.h"
#include "components/search_engines/template_url_service.h"
#include "content/public/browser/web_contents.h"
#include "content/public/test/browser_test.h"
#include "content/public/test/url_loader_interceptor.h"
#include "ui/events/keycodes/keyboard_codes.h"
#include "ui/views/controls/textfield/textfield.h"
#include "ui/views/view_utils.h"
#include "ui/views/widget/widget.h"

namespace {

views::Textfield* FindInput(views::View* view) {
  if (auto* input = views::AsViewClass<views::Textfield>(view)) {
    return input;
  }
  for (views::View* child : view->children()) {
    if (auto* input = FindInput(child)) {
      return input;
    }
  }
  return nullptr;
}

class ArcCommandBarBrowserTest : public InProcessBrowserTest {
 protected:
  void SetUpCommandLine(base::CommandLine* command_line) override {
    command_line->AppendSwitch("disable-default-apps");
  }
  views::Widget* OpenPalette() {
    EXPECT_TRUE(chrome::ExecuteCommand(browser(), IDC_NEW_TAB));
    auto* parent =
        BrowserView::GetBrowserViewForBrowser(browser())->GetWidget();
    for (views::Widget* widget :
         views::Widget::GetAllOwnedWidgets(parent->GetNativeView())) {
      if (widget->GetName() == "ArcCommandBar") {
        return widget;
      }
    }
    return nullptr;
  }
  void Key(views::Widget* widget, ui::KeyboardCode key, bool command = false) {
    ASSERT_TRUE(ui_test_utils::SendKeyPressToWindowSync(
        widget->GetNativeWindow(), key, false, false, false, command));
  }
};

IN_PROC_BROWSER_TEST_F(ArcCommandBarBrowserTest,
                       ThemeLayoutCanHideAndRestoreSidebar) {
  auto* view = BrowserView::GetBrowserViewForBrowser(browser());
  ASSERT_TRUE(view->IsZenModeEnabledForLayout());
  EXPECT_TRUE(view->IsZenModeSideChromePinned());
  EXPECT_TRUE(view->IsZenModeTopChromePinned());
  view->ToggleZenModeSideChrome();
  EXPECT_FALSE(view->IsZenModeSideChromePinned());
  EXPECT_TRUE(view->IsZenModeTopChromePinned());
  view->ToggleZenModeSideChrome();
  EXPECT_TRUE(view->IsZenModeSideChromePinned());
}

IN_PROC_BROWSER_TEST_F(ArcCommandBarBrowserTest,
                       FocusLocationOnHomeOpensCommandBarWithoutPinningSidebar) {
  auto* view = BrowserView::GetBrowserViewForBrowser(browser());
  view->ToggleZenModeSideChrome();
  ASSERT_FALSE(view->IsZenModeSideChromePinned());
  ASSERT_TRUE(chrome::ExecuteCommand(browser(), IDC_FOCUS_LOCATION));
  EXPECT_TRUE(OpenPalette());
  EXPECT_FALSE(view->IsZenModeSideChromePinned());
}

IN_PROC_BROWSER_TEST_F(ArcCommandBarBrowserTest,
                       EmptyEnterAndCancellationCreateNoTab) {
  const int count = browser()->tab_strip_model()->count();
  auto* palette = OpenPalette();
  ASSERT_TRUE(palette);
  EXPECT_EQ(count, browser()->tab_strip_model()->count());
  Key(palette, ui::VKEY_RETURN);
  EXPECT_EQ(count, browser()->tab_strip_model()->count());
  Key(palette, ui::VKEY_TAB);
  Key(palette, ui::VKEY_ESCAPE);
  base::RunLoop().RunUntilIdle();
  EXPECT_EQ(count, browser()->tab_strip_model()->count());
}

IN_PROC_BROWSER_TEST_F(ArcCommandBarBrowserTest,
                       SubmittingUrlCreatesExactlyOneTab) {
  const int count = browser()->tab_strip_model()->count();
  auto* palette = OpenPalette();
  ASSERT_TRUE(palette);
  auto* input = FindInput(palette->GetContentsView());
  ASSERT_TRUE(input);
  helium::SetArcCommandBarInputForTesting(browser(), u"about:blank");
  Key(palette, ui::VKEY_RETURN);
  base::RunLoop().RunUntilIdle();
  EXPECT_EQ(count + 1, browser()->tab_strip_model()->count());
  EXPECT_EQ(
      GURL("about:blank"),
      browser()->tab_strip_model()->GetActiveWebContents()->GetVisibleURL());
}

IN_PROC_BROWSER_TEST_F(ArcCommandBarBrowserTest,
                       ExplicitUrlQueryWinsOverQuestionRouting) {
  auto* palette = OpenPalette();
  ASSERT_TRUE(palette);
  auto* input = FindInput(palette->GetContentsView());
  ASSERT_TRUE(input);
  helium::SetArcCommandBarInputForTesting(browser(), u"about:blank?why=how are you");
  Key(palette, ui::VKEY_RETURN);
  base::RunLoop().RunUntilIdle();
  EXPECT_EQ(
      GURL("about:blank?why=how%20are%20you"),
      browser()->GetTabStripModel()->GetActiveWebContents()->GetVisibleURL());
}

IN_PROC_BROWSER_TEST_F(ArcCommandBarBrowserTest,
                       LocalModeNeverRequestsSearchSuggestions) {
  browser()->GetProfile()->GetPrefs()->SetBoolean(helium::kArcOnlineSuggestions, false);
  auto* service =
      TemplateURLServiceFactory::GetForProfile(browser()->GetProfile());
  search_test_utils::WaitForTemplateURLServiceToLoad(service);
  TemplateURLData data;
  data.SetShortName(u"Test search");
  data.SetKeyword(u"arc-test");
  data.SetURL("https://arc-search.invalid/?q={searchTerms}");
  data.suggestions_url = "https://arc-suggestions.invalid/?q={searchTerms}";
  auto* engine = service->Add(std::make_unique<TemplateURL>(data));
  service->SetUserSelectedDefaultSearchProvider(engine);
  std::atomic<int> suggestion_requests{0};
  content::URLLoaderInterceptor interceptor(base::BindLambdaForTesting(
      [&](content::URLLoaderInterceptor::RequestParams* params) {
        if (params->url_request.url.host() == "arc-suggestions.invalid") {
          ++suggestion_requests;
        }
        return false;
      }));
  auto* palette = OpenPalette();
  ASSERT_TRUE(palette);
  // Even the early prefixes, before the text becomes an English question,
  // must stay away from the search engine's suggestion endpoint.
  for (const auto key : {ui::VKEY_W, ui::VKEY_H, ui::VKEY_Y, ui::VKEY_SPACE,
                         ui::VKEY_A, ui::VKEY_B, ui::VKEY_C}) {
    Key(palette, key);
  }
  base::RunLoop settle;
  base::SingleThreadTaskRunner::GetCurrentDefault()->PostDelayedTask(
      FROM_HERE, settle.QuitClosure(), base::Seconds(1));
  settle.Run();
  EXPECT_EQ(0, suggestion_requests.load());
  Key(palette, ui::VKEY_ESCAPE);
}

IN_PROC_BROWSER_TEST_F(ArcCommandBarBrowserTest, OnlineModeRequestsDefaultEngineSuggestions) {
  browser()->GetProfile()->GetPrefs()->SetBoolean(helium::kArcOnlineSuggestions, true);
  auto* service = TemplateURLServiceFactory::GetForProfile(browser()->GetProfile());
  search_test_utils::WaitForTemplateURLServiceToLoad(service);
  TemplateURLData data;
  data.SetShortName(u"Test search");
  data.SetKeyword(u"arc-test");
  data.SetURL("https://arc-search.invalid/?q={searchTerms}");
  data.suggestions_url = "https://arc-suggestions.invalid/?q={searchTerms}";
  service->SetUserSelectedDefaultSearchProvider(service->Add(std::make_unique<TemplateURL>(data)));
  std::atomic<int> suggestion_requests{0};
  content::URLLoaderInterceptor interceptor(base::BindLambdaForTesting(
      [&](content::URLLoaderInterceptor::RequestParams* params) {
        if (params->url_request.url.host() != "arc-suggestions.invalid") return false;
        ++suggestion_requests;
        content::URLLoaderInterceptor::WriteResponse(
            "HTTP/1.1 200 OK\nContent-Type: application/json\n\n",
            "[\"rainbow\",[\"rainbow colors\"]]", params->client.get());
        return true;
      }));
  auto* palette = OpenPalette();
  ASSERT_TRUE(palette);
  helium::SetArcCommandBarInputForTesting(browser(), u"rainbow");
  base::RunLoop settle;
  base::SingleThreadTaskRunner::GetCurrentDefault()->PostDelayedTask(
      FROM_HERE, settle.QuitClosure(), base::Seconds(1));
  settle.Run();
  EXPECT_GT(suggestion_requests.load(), 0);
  Key(palette, ui::VKEY_ESCAPE);
}

IN_PROC_BROWSER_TEST_F(ArcCommandBarBrowserTest, RepeatedShortcutReusesPalette) {
  auto* first = OpenPalette();
  ASSERT_TRUE(first);
  EXPECT_EQ(first, OpenPalette());
  Key(first, ui::VKEY_ESCAPE);
}

IN_PROC_BROWSER_TEST_F(ArcCommandBarBrowserTest, CommandEnterSearchesRawQuestionAfterSelectionMoves) {
  auto* service = TemplateURLServiceFactory::GetForProfile(browser()->GetProfile());
  search_test_utils::WaitForTemplateURLServiceToLoad(service);
  TemplateURLData data;
  data.SetShortName(u"Test search");
  data.SetKeyword(u"arc-test");
  data.SetURL("https://arc-search.invalid/?q={searchTerms}");
  service->SetUserSelectedDefaultSearchProvider(service->Add(std::make_unique<TemplateURL>(data)));
  auto* palette = OpenPalette();
  ASSERT_TRUE(palette);
  helium::SetArcCommandBarInputForTesting(browser(), u"why is the sky blue");
  Key(palette, ui::VKEY_DOWN);
  Key(palette, ui::VKEY_RETURN, true);
  base::RunLoop().RunUntilIdle();
  EXPECT_EQ(service->GenerateSearchURLForDefaultSearchProvider(u"why is the sky blue"),
            browser()->GetTabStripModel()->GetActiveWebContents()->GetVisibleURL());
}

}  // namespace
