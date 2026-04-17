/**
 * Chart configuration constants for DataChart component.
 * Centralizes all magic numbers used in chart rendering.
 */

export const CHART_CONFIG = {
  // Dimensions
  HEIGHT: 220,
  BAR_MAX_SIZE: 60,
  HORIZONTAL_BAR_ROW_HEIGHT: 40,
  PIE_INNER_RADIUS: 45,
  PIE_OUTER_RADIUS: 75,
  PIE_PADDING_ANGLE: 2,

  // Data limits
  MAX_PIE_ITEMS: 6,
  DATA_AGGREGATION_THRESHOLD: 12,
  DATA_BUCKET_DIVISOR: 10,

  // Labels
  LABEL_MAX_LENGTH: 12,
  PIE_LABEL_MAX_LENGTH: 8,
  Y_AXIS_LABEL_MAX_LENGTH: 10,
  TRUNCATION_SUFFIX: '...',

  // Axis formatting
  X_AXIS_ROTATION_DEGREES: -20,
  X_AXIS_HEIGHT: 50,

  // Dot sizes
  DOT_RADIUS: 3,
  DOT_ACTIVE_RADIUS: 5,

  // Bar radius (top-left, top-right, bottom-right, bottom-left)
  HORIZONTAL_BAR_RADIUS: [0, 6, 6, 0] as [number, number, number, number],

  // Margins
  MARGINS: { top: 10, right: 10, left: -5, bottom: 5 },

  // Dash pattern for reference lines
  DASH_PATTERN: '5 5',

  // Gradient opacity
  GRADIENT_OPACITY_TOP: 0.3,
  GRADIENT_OPACITY_BOTTOM: 0,
} as const;

// Indian number formatting thresholds
export const NUMBER_FORMAT = {
  CRORE: 10000000,
  LAKH: 100000,
  THOUSAND: 1000,
  DECIMAL_PLACES: 1,
} as const;
