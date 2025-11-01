/** @odoo-module **/

import { NavBar } from '@web/webclient/navbar/navbar';

import { _t } from '@web/core/l10n/translation';
import { patch } from '@web/core/utils/patch';
import { browser } from '@web/core/browser/browser';
import { cookie } from '@web/core/browser/cookie';
import { useSortable } from '@web/core/utils/sortable_owl';
import { useService, useBus } from '@web/core/utils/hooks';
import { useHotkey } from '@web/core/hotkeys/hotkey_hook';
import { computeAppsAndMenuItems, reorderApps } from '@web/webclient/menus/menu_helpers';
import { onWillStart, useState, useRef, useExternalListener } from '@odoo/owl';

import { useUdooStore, useUdooLocalStore } from '../webclient';
import { VIEW_IMAP } from '../action_utils';


patch(NavBar.prototype, {
    setup() {
        super.setup();
        this.user = this.env.services.user;
        this.orm = this.env.services.orm;
        this.ui = this.env.services.ui;
        this.uo = useUdooStore();
        this.ue = useUdooLocalStore();

        this.view_imap = VIEW_IMAP;

        const menuOrder = JSON.parse(this.user?.settings?.ps_menu_orders || 'null');
        const menuApps = computeAppsAndMenuItems(this.menuService.getMenuAsTree('root')).apps;
        this.originApps = Array.of(...menuApps);

        if (menuOrder) reorderApps(menuApps, menuOrder);
        this.uo.orderedApps = menuApps;

        this.state = useState({
            isopen: false,
            focusix: null,
            ui_view: 'app',
        });

        this.island = useRef('island');
        this.islandContextMenu = useRef('island_context');

        useHotkey('escape', () => this.toggleWorkspace());

        /* Favorites sortable */
        this.favDragRoot = useRef('fav_drag_root');
        useSortable({
            ref: this.favDragRoot,
            elements: '.u_draggable',
            applyChangeOnDrop: true,
            cursor: 'move',
            delay: 500,
            onWillStartDrag: (params) => this._sortFavStart(params),
            onDrop: (params) => this._sortFavDrop(params),
        });

        /* Bookmarks sortable */
        this.bmkDragRoot = useRef('bookmark_drag_root');
        useSortable({
            ref: this.bmkDragRoot,
            elements: '.dropdown-item',
            applyChangeOnDrop: true,
            cursor: 'move',
            onDragStart: (params) => this._sortBmkStart(params),
            onDrop: (params) => this._sortBmkDrop(params),
        });

        /* Recents form */
        useBus(this.env.bus, 'UDOO:FRC', ({ detail }) => {
            this.uo.recents.push({
                type: 'ir.actions.act_window',
                res_model: detail.resModel,
                name: detail.displayName,
                res_id: detail.resId,
                view_mode: 'form',
                views: [[false, 'form']],
                act_class: this.currentApp.name,
            });
            if (this.uo.recents.length > 80) {
                this.uo.recents.shift();
            }
        });

        /* On click outside app island */
        useExternalListener(window, 'click', this.onWindowClicked, { capture: true });

        onWillStart(async () => {
            this.parseFavMenus();
            this.ui.color_scheme = cookie.get('color_scheme');
        });
    },

    onWindowClicked(ev) {
        // When click outside the showing subnav
        if (this.uo.subnav_shown) {
            const subnav = $('.subnav.show');
            if (subnav && !subnav[0].contains(ev.target)) {
                this.hideSubnav(subnav);
            }
        }

        this.hideCxIsland();

        // Return if already closed
        if (!this.state.isopen || ev.target.id === 'island_toggler' || this.onBmkSort) {
            return;
        }
        const gotClickedInside = this.island.el.contains(ev.target);
        if (!gotClickedInside) {
            this.state.isopen = false;
        }
    },

    hideCxIsland() {
        this.islandContextMenu.el?.classList.remove('show');
    },

    onIslandContext(ev) {
        const el = ev.target.closest('a');

        this.state.currentMenuXmlid = el.dataset.menuXmlid;

        setTimeout(() => {
            this.islandContextMenu.el.classList.add('show');

            const isOverX = ev.x + this.islandContextMenu.el.clientWidth > screen.width;
            const isOverY = ev.y + this.islandContextMenu.el.clientHeight > screen.height;

            if (!isOverX && !isOverY) {
                this.islandContextMenu.el.style.top = `${ev.y - el.clientHeight}px`;
                this.islandContextMenu.el.style.left = `${ev.x}px`;
                this.islandContextMenu.el.style.bottom = 'auto';
                this.islandContextMenu.el.style.right = 'auto';
            } else if (isOverX && isOverY) {
                this.islandContextMenu.el.style.top = 'auto';
                this.islandContextMenu.el.style.left = 'auto';
                this.islandContextMenu.el.style.bottom = '5px';
                this.islandContextMenu.el.style.right = '5px';
            } else if (isOverX) {
                this.islandContextMenu.el.style.top = `${ev.y - el.clientHeight}px`;
                this.islandContextMenu.el.style.left = 'auto';
                this.islandContextMenu.el.style.bottom = 'auto';
                this.islandContextMenu.el.style.right = '5px';
            } else if (isOverY) {
                this.islandContextMenu.el.style.top = 'auto';
                this.islandContextMenu.el.style.left = `${ev.x}px`;
                this.islandContextMenu.el.style.bottom = '5px';
                this.islandContextMenu.el.style.right = 'auto';
            }
        }, 77);
    },

    contextPinStart() {
        return this.uo.fav_menus.includes(this.state.currentMenuXmlid);
    },

    appinNewTab() {
        const cApp = this.originApps.find((el) => el.xmlid === this.state.currentMenuXmlid);
        if (cApp) window.open(this.getMenuItemHref(cApp), '_blank').focus();
    },

    async pinToStart() {
        this.uo.fav_menus.push(this.state.currentMenuXmlid);
        await this.env.services.user.setUserSettings('ps_fav_menus', JSON.stringify(this.uo.fav_menus));
    },

    async unpinFromStart() {
        const newFavs = this.uo.fav_menus.filter((o) => o !== this.state.currentMenuXmlid);
        this.uo.fav_menus = newFavs;
        await this.env.services.user.setUserSettings('ps_fav_menus', JSON.stringify(newFavs));
    },

    async setHomeAction() {
        await this.env.services.user.setUserSettings('ps_start_xmlid', this.state.currentMenuXmlid);
        this.env.services.notification.add(
            _t('Home action has been set!'),
            {
                title: _t('Notification'),
                type: 'success',
            }
        );
    },

    async pinThemAllStart() {
        const newFavs = this.originApps.map((app) => app.xmlid);
        this.uo.fav_menus = newFavs;
        await this.env.services.user.setUserSettings('ps_fav_menus', JSON.stringify(newFavs));
        this.state.ui_view = 'app';
    },

    toggleWorkspace() {
        this.state.isopen = !this.state.isopen;
        if (this.state.isopen) {
            this.state.ui_view = this.ue.sidenav ? 'all_app' : 'app';
        }
    },

    switchSpace(ev) {
        const el = $(ev.target).closest('.nav-link')[0];
        if (this.state.ui_view != el.dataset.tab)
            this.state.ui_view = el.dataset.tab;
    },

    onSelectMenu(menu) {
        this.onNavBarDropdownItemSelection(menu);
        setTimeout(() => {
            this.state.isopen = false;
            this.hideSubnav();
        }, 77);
    },

    async switchLang(lang) {
        if (lang === this.user?.lang) return;

        await this.orm.write('res.users', [this.user?.userId], { lang });
        this.ui.block();
        this.actionService.doAction('reload_context');
    },

    switchColorScheme(ev) {
        const target = this.ui.color_scheme === 'dark' ? 'light' : 'dark';
        cookie.set('color_scheme', target);
        this.ui.block();
        browser.location.reload();
    },

    _sortFavStart({ element, addClass }) {
        addClass(element.children[0], 'u_dragged_app');
    },

    async _sortFavDrop({ element, previous }) {
        const order = this.uo.orderedApps.map((app) => app.xmlid);
        const menuXmlid = element.children[0].dataset.menuXmlid;
        const elementIndex = order.indexOf(menuXmlid);

        order.splice(elementIndex, 1);
        if (previous) {
            const prevIndex = order.indexOf(previous.children[0].dataset.menuXmlid);
            order.splice(prevIndex + 1, 0, menuXmlid);
        } else {
            order.splice(0, 0, menuXmlid);
        }

        // apply new order and sync
        reorderApps(this.uo.orderedApps, order);
        await this.user?.setUserSettings('ps_menu_orders', JSON.stringify(order));
    },

    _sortBmkStart({ element, addClass }) {
        this.onBmkSort = true;
    },

    async _sortBmkDrop({ element, previous }) {
        const bookmarks = this.ui.bookmarks;

        const order = bookmarks.map((app) => app.act_uid);
        const actUid = element.dataset.uid;
        const elementIndex = order.indexOf(actUid);

        order.splice(elementIndex, 1);
        if (previous) {
            const prevIndex = order.indexOf(previous.dataset.uid);
            order.splice(prevIndex + 1, 0, actUid);
        } else {
            order.splice(0, 0, actUid);
        }

        // save new order and sync
        const newBookmarks = order.map(o => bookmarks.find(bm => bm.act_uid === o));
        this.ui.bookmarks = newBookmarks;
        await this.env.services.user.setUserSettings('up_bookmarks', JSON.stringify(newBookmarks));
        this.onBmkSort = false;
    },

    _isCurrentApp(app) {
        if (this.currentApp && app) {
            return this.currentApp.id === app.id;
        }
        return false;
    },

    onShowSubnav(ev) {
        ev.preventDefault();
        ev.stopPropagation();

        this.onSubnavLeave(null);

        const navItem = ev.target.closest('.nav-item');
        const subNav = navItem.querySelector('.subnav');
        const ppLink = navItem.querySelector('a');
        if (subNav) {
            this.uo.subnav_shown = ppLink.dataset.menuXmlid;
            this.onReactSubnav(navItem.getBoundingClientRect(), subNav);
        }
    },

    onReactSubnav(tRect, subNav) {
        const tPadding = 50;
        const bPadding = 5;
        const hPanel = $(subNav).outerHeight(true);
        const vBalance = (hPanel - tRect.height) / 2;
        let alignedTop = tRect.top - vBalance;

        if (alignedTop <= tPadding) {
            alignedTop = tPadding;
        } else if ((alignedTop + hPanel) >= (window.innerHeight - tPadding)) {
            alignedTop = 0;
        }
        if (alignedTop) {
            subNav.style.top = `${alignedTop}px`;;
        } else {
            subNav.style.bottom = `${bPadding}px`;
            subNav.style.top = null;
        }
        subNav.classList.add('show');
    },

    onSubnavLeave(ev) {
        this.uo.subnav_shown = false;
        const subNav = ev?.target || $('.subnav.show')[0];
        if (subNav) {
            subNav.classList.remove('show');
        }
    },

    hideSubnav(qel = false) {
        if (this.uo.subnav_shown) {
            const subnav = qel || $('.subnav.show');
            this.uo.subnav_shown = false;
            subnav.removeClass('show');
        }
    },

    async openRecentAction(action) {
        this.ui.block_recent = true;
        await this.actionService.doAction(action);
        setTimeout(() => {
            this.state.isopen = false;
        }, 77);
    },

    parseFavMenus() {
        this.uo.fav_menus = JSON.parse(this.user?.settings?.ps_fav_menus || '[]');
    },

    get currentApp() {
        if (this.monkeyApp)
            return this.menuService.getMenu(this.monkeyApp);
        else
            return super.currentApp;
    },

    getAppSections(id) {
        this.monkeyApp = id;
        const monkeySections = this.currentAppSections;
        this.monkeyApp = false;
        return monkeySections;
    },

    evaida(webIconData) {
        const prefix = webIconData.startsWith('P')
            ? 'data:image/svg+xml;base64,'
            : 'data:image/png;base64,';
        return webIconData.startsWith('data:image')
            ? webIconData
            : prefix + webIconData.replace(/\s/g, '');
    }
});