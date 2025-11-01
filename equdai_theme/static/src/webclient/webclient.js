/** @odoo-module **/

import { loadLanguages, _t } from '@web/core/l10n/translation';
import { patch } from '@web/core/utils/patch';
import { browser } from '@web/core/browser/browser';
import { useHotkey } from '@web/core/hotkeys/hotkey_hook';
import { useService, useBus } from '@web/core/utils/hooks';
import { useCommand } from '@web/core/commands/command_hook';
import { isMacOS } from '@web/core/browser/feature_detection';
import { registry } from '@web/core/registry';
import { WebClient } from '@web/webclient/webclient';
import { ResizablePanel } from '@web/core/resizable_panel/resizable_panel';
import { reactive, useState, onWillStart, onMounted, useExternalListener } from '@odoo/owl';

import { CommandPalette } from './trays/quick_search';
import { bookmarkPalette, actionBookmarkThis, openBookmarkPalette } from './bookmark';
import { BookmarkManager } from './trays/bookmark';

const trayMenu = registry.category('systray');

// Memorized store
const jsonStore = (obj, key) => {
    localStorage.setItem(key, JSON.stringify(obj));
};
const lstore = reactive({}, () => jsonStore(lstore, 'udoo'));
export function useUdooLocalStore(initialst = {}) {
    Object.assign(lstore, JSON.parse(localStorage.getItem('udoo')) || initialst);
    jsonStore(lstore, 'udoo');
    return useState(lstore);
}

// Global store (non-memorized)
export const ustore = reactive({ recents: [] });
export function useUdooStore() {
    return useState(ustore);
}


patch(WebClient.prototype, {
    setup() {
        super.setup();
        // Get services from environment with fallbacks
        this.ui = this.env.services.ui;
        this.userService = this.env.services.user;
        this.hotkey = this.env.services.hotkey;
        this.action = this.env.services.action;
        this.uo = useUdooStore();

        // Initialize currentCompany with fallback
        this.currentCompany = this.env.services.company?.currentCompany || { id: 1 };

        this.ue = useUdooLocalStore({
            sidenav: !this.env.isSmall,
            sidenavWidth: (window.odoo?.omux?.sidenav?.def_width) || 243,
            companyId: this.currentCompany.id,

        });

      


        /* Set web page title by config */
        if (window.odoo?.omux?.web?.title_prefix) {
            this.title.setParts({ zopenerp: window.odoo.omux.web.title_prefix });
        }

        /* Bookmark manager command */
        useCommand(
            _t('Bookmark current tab'),
            () => { actionBookmarkThis(this.env); },
            {
                category: 'smart_action',
                global: true,
                isAvailable: () => this.env.services.action.currentController,
            }
        );
        useCommand(
            _t('Bookmark manager'),
            () => (bookmarkPalette),
            {
                category: 'smart_action',
                global: true,
            }
        );
        useHotkey('alt+k', () => openBookmarkPalette(this.env), {
            bypassEditableProtection: true,
            global: true,
        });

        /* Bookmark manager system tray */
        trayMenu.add('bookmark', { Component: BookmarkManager }, { sequence: 50 });

        /* Quick action system tray */
        trayMenu.add('quick_search', { Component: CommandPalette }, { sequence: 50 });

        /* Side nav state */
        useHotkey('control+shift+arrowleft', () => {
            this.onSassLsideFold(), {
                bypassEditableProtection: true,
                global: true,
            }
        });

        /* Holding key handling */
        useBus(this.env.bus, 'ACTION_MANAGER:UI-UPDATED', (mode) => {
            // Clear key holding state
            this.ui.ctrlKey = false;
            this.ui.shiftKey = false;
        });

        onWillStart(async () => {
            this.uo.ps_auto_hmenu = this.userService?.settings?.ps_auto_hmenu;
            this.ui.bookmarks = this.parseBookmarks();
            const languages = await loadLanguages(this.orm);
            this.ui.languages = languages;
        });

        onMounted(() => {
            this.ui._auid = this.router.current.hash.action;

            this._loadSidenavState();
            this._loadRecents();
        });

        useExternalListener(window, 'beforeunload', () => {
            /* Recents post process */
            const localRecent = browser.localStorage.getItem('rc');
            const lastRecent = JSON.parse(localRecent) || [];
            const mergeArray = lastRecent.concat(this.uo.recents);
            mergeArray.forEach(el => {
                el.act_uid = el.act_uid || JSON.stringify(el);
            });
            const uniqueArray = [];
            for (let index = mergeArray.length - 1; index >= 0; index--) {
                const el = mergeArray[index];
                if (uniqueArray.findIndex(o => o.act_uid === el.act_uid) == -1) {
                    uniqueArray.push(el);
                }
            }
            this._saveRecents(uniqueArray.reverse());

            /* Bookmark post process */
            if (this.ui.bookmarks.length == 0) {
                return;
            }
            const bookmarks = [];
            for (let index = this.ui.bookmarks.length - 1; index >= 0; index--) {
                const el = this.ui.bookmarks[index];
                if (el.pinned || bookmarks.findIndex(o => o.act_uid === el.act_uid) === -1) {
                    bookmarks.push(el);
                }
            }
            this.userService?.setUserSettings('up_bookmarks', JSON.stringify(bookmarks.reverse()));
        });
    },

    onGlobalClick(ev) {
        // Save ctrl holding state
        this.env.services.ui.ctrlKey = ev.ctrlKey || (isMacOS() && ev.metaKey);
        this.env.services.ui.shiftKey = ev.shiftKey;

        super.onGlobalClick(ev);
    },

    _loadSidenavState() {
        if (this.ue.sidenav) {
            document.body.classList.remove('nolside');
        } else {
            document.body.classList.add('nolside');
        }
    },

    async _loadDefaultApp() {
        // Get company menu preset for initial user
        const favconf = this.userService?.settings?.ps_fav_menus;
        if (!favconf || favconf == '[]') {
            this.uo.apps_preset = await this.orm.silent.call('res.company', 'get_menus_preset', [[this.currentCompany.id]]);
            if (this.uo.apps_preset) {
                const newfav = [];
                this.uo.orderedApps.forEach(app => {
                    if (this.uo.apps_preset.includes(app.id)) {
                        newfav.push(app.xmlid);
                    }
                });
                this.uo.fav_menus = newfav;
                await this.userService?.setUserSettings('ps_fav_menus', JSON.stringify(newfav));
            }
        }
        // Start action logic
        const root = this.menuService.getMenu('root');
        for (const app of root.childrenTree) {
            if (app.xmlid === this.userService?.settings?.ps_start_xmlid) {
                return this.menuService.selectMenu(app);
            }
        }
        return super._loadDefaultApp();
    },

    _onSideNavResize(width) {
        if (width > ((window.odoo?.omux?.sidenav?.max_width) || 320))
            return;
        const sidenav = document.querySelector('.o_sidenav');
        if (!sidenav)
            return;

        if (width < 142) {
            sidenav.classList.add('sm');
        } else {
            sidenav.classList.remove('sm');
        }

        this.ue.sidenavWidth = width;
        document.documentElement.style.setProperty('--uw-sidenav', `${width}px`);

        // Refresh column width when has list view
        this.env.bus.trigger('TREE:OMCL');
    },

    _loadRecents() {
        const lastRecent = browser.localStorage.getItem('rc');
        if (lastRecent) {
            this.uo.recents = JSON.parse(lastRecent);
        }
    },

    _saveRecents(rc = false) {
        browser.localStorage.setItem('rc', JSON.stringify(rc || this.uo.recents));
    },

    toggleFootnav() {
        this.ue.footnav = !this.ue.footnav;
    },

    parseBookmarks() {
        return JSON.parse(this.userService?.settings?.up_bookmarks || '[]');
    },

    onSassLsideFold() {
        this.ue.sidenav = !this.ue.sidenav && !this.env.isSmall;
        this._loadSidenavState();

        // Refresh column width when has list view
        this.env.bus.trigger('TREE:OMCL');
    },

    openOmSearch() {
        this.env.services.command.openMainPalette({
            searchValue: '/',
            bypassEditableProtection: true,
            global: true,
        });
    }
});

WebClient.components = { ...WebClient.components, ResizablePanel }
