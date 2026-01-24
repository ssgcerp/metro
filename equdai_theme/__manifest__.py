# -*- coding: utf-8 -*-
# Copyright 2024 Jupetern

{
    'name': 'Equdai Theme',
    'category': 'Themes/Backend',
    'summary': 'Equdai',
    'version': '19.0.1.0.0',
    'license': 'OPL-1',
    'author': 'Jupetern',
    'website': 'https://www.linkedin.com/in/jupetern',
    'sequence': 777,
    'images': [
        'static/description/banner.png',
        'static/description/theme_screenshot.png',
    ],
    'depends': [
        'base',
        'auth_signup',
        'web',
    ],
    'excludes': [
        'web_enterprise',
    ],
    'data': [
        'views/webclient_templates.xml',
        'views/res_company_views.xml',
    ],
    'assets': {
        'web._assets_primary_variables': [
            ('prepend', 'equdai_theme/static/src/scss/style_variables.scss'),
            (
                'before',
                'web/static/src/scss/primary_variables.scss',
                'equdai_theme/static/src/scss/primary_variables.scss',
            ),
            ('before', 'web/static/src/**/*.variables.scss', 'equdai_theme/static/src/**/*.variables.scss'),
        ],
        'web._assets_secondary_variables': [
            (
                'before',
                'web/static/src/scss/secondary_variables.scss',
                'equdai_theme/static/src/scss/secondary_variables.scss',
            ),
        ],
        'web._assets_bootstrap': [
            'equdai_theme/static/src/scss/overridden_common.scss',
        ],
        'web._assets_backend_helpers': [
            (
                'before',
                'web/static/src/scss/bootstrap_overridden.scss',
                'equdai_theme/static/src/scss/bs_backend_overridden.scss',
            ),
        ],
        'web.assets_web': [
            (
                'after',
                'equdai_theme/static/src/scss/style_variables.scss',
                'equdai_theme/static/src/scss/omux/light.scss',
            ),
            # Include backend assets in web assets as well
            'equdai_theme/static/src/webclient/**/*',
            'equdai_theme/static/src/views/**/*',
            'equdai_theme/static/src/search/**/*',
            'equdai_theme/static/src/core/**/*',
            'equdai_theme/static/src/patch/**/*',
            'equdai_theme/static/src/scss/style_backend.scss',
            'equdai_theme/static/src/scss/overridden_icons.scss',
            ('remove', 'equdai_theme/static/src/**/*.dark.scss'),
        ],
        'web.dark_mode_variables': [
            (
                'before',
                'equdai_theme/static/src/scss/primary_variables.scss',
                'equdai_theme/static/src/scss/primary_variables_dark.scss',
            ),
            (
                'before',
                'equdai_theme/static/src/**/*.variables.scss',
                'equdai_theme/static/src/**/*.variables.dark.scss',
            ),
            (
                'before',
                'equdai_theme/static/src/scss/secondary_variables.scss',
                'equdai_theme/static/src/scss/secondary_variables_dark.scss',
            ),
        ],
        'web.assets_web_dark': [
            ('include', 'web.dark_mode_variables'),
            (
                'before',
                'equdai_theme/static/src/scss/bs_backend_overridden.scss',
                'equdai_theme/static/src/scss/bs_backend_overridden_dark.scss',
            ),
            (
                'after',
                'web/static/lib/bootstrap/scss/_functions.scss',
                'equdai_theme/static/src/scss/bs_functions_overridden_dark.scss',
            ),
            'equdai_theme/static/src/**/*.dark.scss',
        ],
        'web.assets_frontend': [
            (
                'before',
                'web/static/lib/bootstrap/scss/_variables.scss',
                'equdai_theme/static/src/scss/bs_frontend_variables.scss',
            ),
            (
                'after',
                'web/static/src/scss/fontawesome_overridden.scss',
                'equdai_theme/static/src/scss/overridden_icons.scss',
            ),
            (
                'replace',
                'web/static/src/webclient/navbar/navbar.scss',
                'equdai_theme/static/src/webclient/navbar/navbar.scss',
            ),
        ],
        'web._assets_core': [
            'equdai_theme/static/src/core/**/*',
            (
                'after',
                'web/static/src/session.js',
                'equdai_theme/static/src/omux.js',
            ),
        ],
        # COLOR
        'web.assets_web_magenta': [
            ('include', 'web.assets_web'),
            (
                'after',
                'equdai_theme/static/src/scss/style_variables.scss',
                'equdai_theme/static/src/scss/pallets/magenta.scss',
            ),
        ],
        'web.assets_web_magenta_dark': [
            ('include', 'web.assets_web_dark'),
            (
                'after',
                'equdai_theme/static/src/scss/style_variables.scss',
                'equdai_theme/static/src/scss/pallets/magenta_dark.scss',
            ),
        ],
        'web.assets_web_dodger': [
            ('include', 'web.assets_web'),
            (
                'after',
                'equdai_theme/static/src/scss/style_variables.scss',
                'equdai_theme/static/src/scss/pallets/dodger.scss',
            ),
        ],
        'web.assets_web_dodger_dark': [
            ('include', 'web.assets_web_dark'),
            (
                'after',
                'equdai_theme/static/src/scss/style_variables.scss',
                'equdai_theme/static/src/scss/pallets/dodger_dark.scss',
            ),
        ],
        'web.assets_web_lime': [
            ('include', 'web.assets_web'),
            (
                'after',
                'equdai_theme/static/src/scss/style_variables.scss',
                'equdai_theme/static/src/scss/pallets/lime.scss',
            ),
        ],
        'web.assets_web_lime_dark': [
            ('include', 'web.assets_web_dark'),
            (
                'after',
                'equdai_theme/static/src/scss/style_variables.scss',
                'equdai_theme/static/src/scss/pallets/lime_dark.scss',
            ),
        ],
        'web.assets_web_green': [
            ('include', 'web.assets_web'),
            (
                'after',
                'equdai_theme/static/src/scss/style_variables.scss',
                'equdai_theme/static/src/scss/pallets/green.scss',
            ),
        ],
        'web.assets_web_green_dark': [
            ('include', 'web.assets_web_dark'),
            (
                'after',
                'equdai_theme/static/src/scss/style_variables.scss',
                'equdai_theme/static/src/scss/pallets/green_dark.scss',
            ),
        ],
        'web.assets_web_emerald': [
            ('include', 'web.assets_web'),
            (
                'after',
                'equdai_theme/static/src/scss/style_variables.scss',
                'equdai_theme/static/src/scss/pallets/emerald.scss',
            ),
        ],
        'web.assets_web_emerald_dark': [
            ('include', 'web.assets_web_dark'),
            (
                'after',
                'equdai_theme/static/src/scss/style_variables.scss',
                'equdai_theme/static/src/scss/pallets/emerald_dark.scss',
            ),
        ],
        'web.assets_web_sky': [
            ('include', 'web.assets_web'),
            (
                'after',
                'equdai_theme/static/src/scss/style_variables.scss',
                'equdai_theme/static/src/scss/pallets/sky.scss',
            ),
        ],
        'web.assets_web_sky_dark': [
            ('include', 'web.assets_web_dark'),
            (
                'after',
                'equdai_theme/static/src/scss/style_variables.scss',
                'equdai_theme/static/src/scss/pallets/sky_dark.scss',
            ),
        ],
        'web.assets_web_rose': [
            ('include', 'web.assets_web'),
            (
                'after',
                'equdai_theme/static/src/scss/style_variables.scss',
                'equdai_theme/static/src/scss/pallets/rose.scss',
            ),
        ],
        'web.assets_web_rose_dark': [
            ('include', 'web.assets_web_dark'),
            (
                'after',
                'equdai_theme/static/src/scss/style_variables.scss',
                'equdai_theme/static/src/scss/pallets/rose_dark.scss',
            ),
        ],
        'web.assets_web_yellow': [
            ('include', 'web.assets_web'),
            (
                'after',
                'equdai_theme/static/src/scss/style_variables.scss',
                'equdai_theme/static/src/scss/pallets/yellow.scss',
            ),
        ],
        'web.assets_web_yellow_dark': [
            ('include', 'web.assets_web_dark'),
            (
                'after',
                'equdai_theme/static/src/scss/style_variables.scss',
                'equdai_theme/static/src/scss/pallets/yellow_dark.scss',
            ),
        ],
        'web.assets_web_orange': [
            ('include', 'web.assets_web'),
            (
                'after',
                'equdai_theme/static/src/scss/style_variables.scss',
                'equdai_theme/static/src/scss/pallets/orange.scss',
            ),
        ],
        'web.assets_web_orange_dark': [
            ('include', 'web.assets_web_dark'),
            (
                'after',
                'equdai_theme/static/src/scss/style_variables.scss',
                'equdai_theme/static/src/scss/pallets/orange_dark.scss',
            ),
        ],
        'web.assets_web_pink': [
            ('include', 'web.assets_web'),
            (
                'after',
                'equdai_theme/static/src/scss/style_variables.scss',
                'equdai_theme/static/src/scss/pallets/pink.scss',
            ),
        ],
        'web.assets_web_pink_dark': [
            ('include', 'web.assets_web_dark'),
            (
                'after',
                'equdai_theme/static/src/scss/style_variables.scss',
                'equdai_theme/static/src/scss/pallets/pink_dark.scss',
            ),
        ],
        'web.assets_web_indigo': [
            ('include', 'web.assets_web'),
            (
                'after',
                'equdai_theme/static/src/scss/style_variables.scss',
                'equdai_theme/static/src/scss/pallets/indigo.scss',
            ),
        ],
        'web.assets_web_indigo_dark': [
            ('include', 'web.assets_web_dark'),
            (
                'after',
                'equdai_theme/static/src/scss/style_variables.scss',
                'equdai_theme/static/src/scss/pallets/indigo_dark.scss',
            ),
        ],
    },
    'price': 127.89,
    'currency': 'USD',
}
