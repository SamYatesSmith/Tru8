const { getDefaultConfig } = require('expo/metro-config');
const { withNativeWind } = require('nativewind/metro');

const config = getDefaultConfig(__dirname);

// Add path aliases
config.resolver.alias = {
  '@': '.',
  '@shared': '../shared',
};

module.exports = withNativeWind(config, { input: './global.css' });