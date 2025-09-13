export const iso = [
    // level 0, always visible
    {
        minStep: 0,
        pointSize: 10,
        pointBorder: 2,
        rectBorder: 8,
        zoomToStep: 0.25,
        fontSize: 'small',
    },
    // level 1, single square takes 1 pixel
    {
        minStep: 1,
        pointSize: 20,
        pointBorder: 2,
        rectBorder: 8,
        zoomToStep: 4,
        fontSize: 'small',
    },
    // level 2, single square takes 8 pixels
    {
        minStep: 8,
        pointSize: 30,
        pointBorder: 2,
        rectBorder: 8,
        zoomToStep: 16,
        fontSize: 'medium',
    },
    // level 3, single square takes 32 pixels
    {
        minStep: 32,
        pointSize: 30,
        pointBorder: 2,
        rectBorder: 8,
        zoomToStep: 32,
        fontSize: 'large',
    }
];

export const top = [
    // level 0, always visible
    {
        minStep: 0,
        pointSize: 10,
        pointBorder: 2,
        rectBorder: 8,
        zoomToStep: 0.25,
        fontSize: 'small',
    },
    // level 1, single square takes 1 pixel
    {
        minStep: 1,
        pointSize: 20,
        pointBorder: 2,
        rectBorder: 8,
        zoomToStep: 4,
        fontSize: 'small',
    },
    // level 2, single square takes 8 pixels
    {
        minStep: 8,
        pointSize: 30,
        pointBorder: 2,
        rectBorder: 8,
        zoomToStep: 16,
        fontSize: 'medium',
    },
    // level 3, single square takes 16 pixels
    {
        minStep: 16,
        pointSize: 30,
        pointBorder: 2,
        rectBorder: 8,
        zoomToStep: 16,
        fontSize: 'large',
    }
];

export var MARK_ZOOM_LEVEL_MIN_STEP = [
    0,     // level 0, always visible
    1,     // level 1, single square takes 1 pixel
    8      // level 2, single square takes 8 pixels
];

export var POINT_SIZE = [
    10,    // level 0
    20,    // level 1
    30     // level 2
];

export var POINT_BORDER_SIZE = [
    2,     // level 0
    2,     // level 1
    2      // level 2
];

export var RECTANGLE_BORDER_SIZE = [
    8,      // level 0
    8,      // level 1
    8,      // level 2
    //16,     // level 1
    //24      // level 2
];

export var ZOOM_TO_STEP = [
    0.2,   // level 0
    4,     // level 1
    16     // level 2
];