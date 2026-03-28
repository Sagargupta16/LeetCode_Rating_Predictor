// Polyfill TextEncoder/TextDecoder for jsdom (jest-environment-jsdom)
// Required because MSW's @mswjs/interceptors uses TextEncoder which
// is not available in the jsdom environment bundled with react-scripts 5.
const { TextEncoder, TextDecoder } = require("util");

Object.assign(global, { TextEncoder, TextDecoder });
