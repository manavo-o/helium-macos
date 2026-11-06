// Copyright 2026 The Helium Authors
// You can use, redistribute, and/or modify this source code under
// the terms of the GPL-3.0 license that can be found in the LICENSE file.

import {html} from '//resources/lit/v3_0/lit.rollup.js';

import type {SettingsAppearanceLayoutPageElement} from './appearance_layout_page.js';

export function getHtml(this: SettingsAppearanceLayoutPageElement) {
  // clang-format off
  return html`<!--_html_template_start_-->
<settings-section page-title="$i18n{layoutPageTitle}">
  <div class="settings-row">Helium Sidebar uses a permanent tab sidebar.
    Drag its divider to resize it from 200 to 480 points.</div>
  <settings-toggle-button class="hr"
      ?hidden="${!this.showVerticalSettings_()}"
      pref-key="helium.browser.vertical_right_aligned"
      label="$i18n{tabStripRightAlign}">
  </settings-toggle-button>



  <settings-toggle-button class="hr"
      pref-key="helium.browser.minimal_location_bar"
      label="$i18n{minimalLocationBar}">
  </settings-toggle-button>
  <settings-toggle-button class="hr"
      pref-key="helium.browser.show_progress_bar"
      label="$i18n{showProgressBar}">
  </settings-toggle-button>
  <div class="settings-row">
    <div class="flex">Interface size (applies after relaunch)</div>
    <settings-dropdown-menu pref-key="helium.browser.arc_interface_density"
        .menuOptions="${[{value: 0, name: 'Compact'}, {value: 1, name: 'Comfortable'}]}">
    </settings-dropdown-menu>
  </div>
  <div class="settings-row">
    <div class="flex">Pinned tile size (applies after relaunch)</div>
    <settings-dropdown-menu pref-key="helium.browser.arc_pinned_tile_size"
        .menuOptions="${[40, 48, 56, 64, 72].map(value => ({value, name: `${value} points`}))}">
    </settings-dropdown-menu>
  </div>
  <settings-toggle-button class="hr"
      pref-key="helium.browser.arc_question_routing"
      label="Route questions to ChatGPT in the command palette"
      sub-label="Private windows always use the default search engine unless you select ChatGPT">
  </settings-toggle-button>
  <settings-toggle-button class="hr"
      pref-key="helium.browser.arc_chat_button"
      label="Show Chat button in the toolbar"
      sub-label="Opens the official ChatGPT extension side panel">
  </settings-toggle-button>
  <settings-toggle-button class="hr"
      pref-key="helium.browser.zen_mode"
      label="$i18n{browserZenMode}"
      sub-label="$i18n{browserZenModeDescription}">
  </settings-toggle-button>
  <div class="list-frame indented-toggles"
      ?hidden="${!this.zenModePref_?.value}">
    <settings-toggle-button class="hr"
        pref-key="helium.browser.zen_mode_sidebar_pinned"
        ?hidden="${!this.showVerticalSettings_()}"
        label="$i18n{zenModePinSidebar}">
    </settings-toggle-button>
    <settings-toggle-button class="hr"
        pref-key="helium.browser.zen_mode_top_chrome_pinned"
        label="$i18n{zenModePinToolbar}">
    </settings-toggle-button>
  </div>
</settings-section>
<!--_html_template_end_-->`;
  // clang-format on
}
