(function ($, $tc, $ctl) {


    $(fullctl.application).on("prefixctl-ready", function (ev, app, id) {
        var prefix_sets = app.$t.prefix_sets;

        $(prefix_sets.$w.list).on("insert:after", (e, prefix_set_row, prefix_set_data) => {
            let monlist = prefix_set_row.data("monlist");
            $(monlist).on("insert:after", (e, monitor_row, monitor_data) => {
                let btnAnnouncements = monitor_row.find('.btn-announcements');
                btnAnnouncements.on('click', function (e) {
                    new $ctl.application.Prefixctl.BGPMonitorReport(prefix_set_data);
                });
            });

        });

    });

    /**
     * Opens a modal showing prefix announcements for a prefix set
     *
     * @class BGPMonitorReport
     * @param {Object} prefix_set
     */

    $ctl.application.Prefixctl.BGPMonitorReport = $tc.extend(
        "BGPMonitorReport",
        {
            BGPMonitorReport: function (prefix_set) {
                var title = "BGP Monitor Report - " + prefix_set.name;
                var element = $('<div>');
                var list = new twentyc.rest.List(
                    $ctl.template('bgp_monitor_report')
                );
                this.list = list;

                list.formatters.asns = (value) => {
                    return value.join(", ");
                }

                // loop through prefix_set.monitors (array) and find the one with `monitor_type` ==
                // `bgp_monitor` and set monitor_id from `id` of that monitor
                let bgp_monitor = null;
                for(let monitor of prefix_set.monitors) {
                    if(monitor.monitor_type === "bgp_monitor") {
                        bgp_monitor = monitor;
                        break;
                    }
                }

                if(!bgp_monitor) {
                    return;
                }

                list.format_request_url = function (url) {
                    return url.replace(/monitor_pk/g, bgp_monitor.id);
                };
                list.load();
                element.append(list.element);
                this.Modal("no_button_lg", title, element);
            }
        },
        $ctl.application.Modal
    );

    /**
     * BGP monitor modal, used for creating and editing BGP monitors
     */
    $ctl.application.Prefixctl.ModalBGPMonitor = $tc.extend(
        "ModalBGPMonitor",
        {
            ModalBGPMonitor: function (prefix_set, monitor) {
                // set properties
                this.prefix_set = prefix_set;
                this.monitor = monitor;
                this.name = "bgp_monitor";

                // get a form instance for the monitor set up form
                this.init_form(monitor);

                // init bgp monitor as a prefix-set monitor
                this.init_prefix_set_monitor()

                this.select_asn_set_origin = new twentyc.rest.Select(
                    this.form.element.find('#asn_set_origin')
                  );
                this.select_asn_set_origin.load();
            }
        },

        // extend from base monitor class
        $ctl.application.Prefixctl.ModalMonitorBase
    )

    // register the monitor
    $ctl.application.Prefixctl.PrefixSetMonitors.register(
        {
            // same as django model handle-ref tag
            name: "bgp_monitor",
            // what namespaces does the viewing user need to be permissioned
            // to to view this monitor
            permissions: ["prefix_monitor"],
            // what is the display name of the monitor
            label: "BGP Monitor",
            // function that opens the monitor modal for creation or editing
            modal: function (prefix_set, monitor) {
                return new $ctl.application.Prefixctl.ModalBGPMonitor(prefix_set, monitor);
            }
        }
    );

})(jQuery, twentyc.cls, fullctl);
