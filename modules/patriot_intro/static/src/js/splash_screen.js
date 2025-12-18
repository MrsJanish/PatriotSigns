/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class PatriotSplash extends Component {
    setup() {
        this.action = useService("action");
        this.title = "Welcome";
    }

    onExploreClick() {
        // Navigate to the main Odoo dashboard or apps menu
        // For now, we'll just show a notification or redirect to 'base.action_res_users' (Users) as an example
        // Or simply trigger the home menu
        this.action.doAction('base.action_res_users_my');
    }
}

PatriotSplash.template = "patriot_intro.SplashScreen";

registry.category("actions").add("patriot_intro.splash", PatriotSplash);
