(function ($, $tc, $ctl) {

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
            permissions: ["bgpmon"],
            // what is the display name of the monitor
            label: "BGP Monitor",
            // function that opens the monitor modal for creation or editing
            modal: function (prefix_set, monitor) {
                return new $ctl.application.Prefixctl.ModalBGPMonitor(prefix_set, monitor);
            }
        }
    );

})(jQuery, twentyc.cls, fullctl);
