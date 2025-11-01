/** @odoo-module **/

// Clamp utility function
function clamp(value, min, max) {
    return Math.min(Math.max(value, min), max);
}

const COLORS_BRIGHT = window.odoo?.omux?.graph?.bright_palette || [];
const COLORS_DARK = window.odoo?.omux?.graph?.dark_palette || [];

/**
 * @param {string} colorScheme
 * @returns {array}
 */
export function getColors(colorScheme) {
    return colorScheme === 'dark' ? COLORS_DARK : COLORS_BRIGHT;
}

/**
 * @param {number} index
 * @param {string} colorScheme
 * @returns {string}
 */
export function getColor(index, colorScheme) {
    const colors = getColors(colorScheme);
    return colors[index % colors.length];
}

export const DEFAULT_BG = '#d3d3d3';

export function getBorderWhite(colorScheme) {
    return colorScheme === 'dark' ? 'rgba(38, 42, 54, .2)' : 'rgba(249,250,251, .2)';
}

const RGB_REGEX = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i;

/**
 * @param {string} hex
 * @param {number} opacity
 * @returns {string}
 */
export function hexToRGBA(hex, opacity) {
    const rgb = RGB_REGEX.exec(hex)
        .slice(1, 4)
        .map((n) => parseInt(n, 16))
        .join(',');
    return `rgba(${rgb},${opacity})`;
}

/**
 * Used to lighten a color
 * @param {string} color
 * @param {number} factor
 * @returns {string}
 */
export function lightenColor(color, factor) {
    factor = clamp(factor, 0, 1);

    let r = parseInt(color.substring(1, 3), 16);
    let g = parseInt(color.substring(3, 5), 16);
    let b = parseInt(color.substring(5, 7), 16);

    r = Math.round(r + (255 - r) * factor);
    g = Math.round(g + (255 - g) * factor);
    b = Math.round(b + (255 - b) * factor);

    r = r.toString(16).padStart(2, '0');
    g = g.toString(16).padStart(2, '0');
    b = b.toString(16).padStart(2, '0');

    return `#${r}${g}${b}`;
}

/**
 * Used to darken a color
 * @param {string} color
 * @param {number} factor
 * @returns {string}
 */
export function darkenColor(color, factor) {
    factor = clamp(factor, 0, 1);

    let r = parseInt(color.substring(1, 3), 16);
    let g = parseInt(color.substring(3, 5), 16);
    let b = parseInt(color.substring(5, 7), 16);

    r = Math.round(r * (1 - factor));
    g = Math.round(g * (1 - factor));
    b = Math.round(b * (1 - factor));

    r = r.toString(16).padStart(2, '0');
    g = g.toString(16).padStart(2, '0');
    b = b.toString(16).padStart(2, '0');

    return `#${r}${g}${b}`;
}
