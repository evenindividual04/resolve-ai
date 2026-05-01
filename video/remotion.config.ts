import { Config } from "@remotion/cli/config";
import { webpackOverride } from "./webpack-override";

Config.overrideWebpackConfig(webpackOverride);

Config.setVideoImageFormat("jpeg");
Config.setPixelFormat("yuv420p");