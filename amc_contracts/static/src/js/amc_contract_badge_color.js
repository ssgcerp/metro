/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { BadgeField } from "@web/views/fields/badge/badge_field";

// Color mapping for Odoo standard colors (0-11)
const COLOR_MAP = {
    0: { bg: '#FFFFFF', fg: '#000000' },
    1: { bg: '#00A09D', fg: '#FFFFFF' },
    2: { bg: '#DE3831', fg: '#FFFFFF' },
    3: { bg: '#EC7C5B', fg: '#FFFFFF' },
    4: { bg: '#A24689', fg: '#FFFFFF' },
    5: { bg: '#7C7FA8', fg: '#FFFFFF' },
    6: { bg: '#4F9FD8', fg: '#FFFFFF' },
    7: { bg: '#00C8D0', fg: '#FFFFFF' },
    8: { bg: '#43A047', fg: '#FFFFFF' },
    9: { bg: '#7BC142', fg: '#000000' },
    10: { bg: '#FBC02D', fg: '#000000' },
    11: { bg: '#F39C12', fg: '#FFFFFF' },
};

patch(BadgeField.prototype, {
    setup() {
        super.setup();
    },

    get style() {
        // Override style getter to apply color from stage_color field
        let baseStyle = super.style || '';
        
        if (this.props.options && this.props.options.color_field) {
            const colorField = this.props.options.color_field;
            const record = this.props.record;
            if (record && record.data && record.data[colorField] !== undefined) {
                const colorValue = record.data[colorField];
                const colorInfo = COLOR_MAP[colorValue] || COLOR_MAP[0];
                return `background-color: ${colorInfo.bg}; color: ${colorInfo.fg}; ${baseStyle}`;
            }
        }
        
        return baseStyle;
    },
});

