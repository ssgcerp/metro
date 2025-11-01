/** @odoo-module **/

import { _t } from '@web/core/l10n/translation';
import { cookie } from '@web/core/browser/cookie';
import { browser } from '@web/core/browser/browser';
import { session } from '@web/session';
import { useService } from '@web/core/utils/hooks';
import { Dialog } from '@web/core/dialog/dialog';
import { CheckBox } from "@web/core/checkbox/checkbox";
import { Component, useState } from '@odoo/owl';

import { useUdooStore } from '../webclient';

export class AppearanceConfig extends Component {
    setup() {
        this.ui = useService('ui');
        this.uo = useUdooStore();
        this.user = useService('user');

        this.title = _t('Appearance');
        this.scheme_data = session.udoo_presets || [];

        this.o_color_shade = cookie.get('color_shade');
        this.o_color_scheme = this.ui.color_scheme || 'light';
        this.state = useState({
            color_shade: this.o_color_shade,
            color_scheme: this.o_color_scheme,
        });
    }

    confirm() {
        if (this.state.color_shade !== this.o_color_shade) {
            cookie.set('color_shade', this.state.color_shade)
            this.ui.block();
            browser.location.reload();
        } else {
            this.user.setUserSettings('ps_auto_hmenu', this.uo.ps_auto_hmenu);
            this.props.close();
        }
    }

    onUoOptionChanged(key, val) {
        this.uo[key] = val;
    }
}

AppearanceConfig.template = 'uweb.AppearanceConfig';
AppearanceConfig.components = {
    Dialog,
    CheckBox,
};