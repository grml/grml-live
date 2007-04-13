-- This file was created by and is modified by Ion.

initialise_screen_id(0, {
    type = "WScreen",
    name = "WScreen",
    subs = {
        {
            type = "WIonWS",
            name = "main",
            split_tree = {
                split_dir = "horizontal",
                split_tls = 512, split_brs = 512,
                tl = {
                    type = "WIonFrame",
                    name = "WIonFrame",
                    flags = 24,
                    saved_y = 0, saved_h = 432,
                    saved_x = 0, saved_w = 1152,
                    subs = {
                    },
                },
                br = {
                    type = "WIonFrame",
                    name = "WIonFrame<1>",
                    flags = 0,
                    subs = {
                    },
                },
            },
            switchto = true,
        },
        {
            type = "WIonWS",
            name = "browse",
            split_tree = {
                type = "WIonFrame",
                name = "WIonFrame<2>",
                flags = 0,
                subs = {
                },
            },
        },
        {
            type = "WFloatWS",
            name = "floating",
            managed = {
                {
                    type = "WFloatFrame",
                    name = "WFloatFrame",
                    flags = 0,
                    subs = {
                        {
                            type = "WClientWin",
                            windowid = 8388620,
                            checkcode = 1,
                            switchto = true,
                        },
                    },
                    geom = { x = 0, y = 0, w = 644, h = 570},
                },
            },
        },
        {
            type = "WIonWS",
            name = "WIonWS",
            split_tree = {
                type = "WIonFrame",
                name = "WIonFrame<4>",
                flags = 0,
                subs = {
                },
            },
        },
    },
})

