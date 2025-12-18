/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { AuroraCanvas } from "./aurora_canvas";

export class ThemeInjector extends Component {
    setup() {
        this.user = useService("user");
        this.orm = useService("orm");
        this.state = useState({ theme: 'clean' });

        onWillStart(async () => {
            try {
                // Fetch the current user's theme setting
                const data = await this.orm.searchRead(
                    "res.users",
                    [["id", "=", this.user.userId]],
                    ["x_patriot_theme"]
                );

                if (data && data.length > 0) {
                    this.state.theme = data[0].x_patriot_theme || 'clean';
                }

                // Set the attribute on body for CSS scoping
                document.body.setAttribute('data-theme', this.state.theme);
            } catch (error) {
                console.error("Theme Load Error:", error);
            }
        });
    }
}

ThemeInjector.template = xml`
    <t>
        <AuroraCanvas t-if="state.theme === 'aurora'"/>
    </t>
`;
ThemeInjector.components = { AuroraCanvas };

// Register in main_components so it is always present
registry.category("main_components").add("PatriotThemeInjector", {
    Component: ThemeInjector,
});
