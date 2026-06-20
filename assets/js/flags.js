import { polyfillCountryFlagEmojis } from "country-flag-emoji-polyfill";
// The package's exports map doesn't expose the woff2, so reach it by file path.
import flagFontUrl from "../../node_modules/country-flag-emoji-polyfill/dist/TwemojiCountryFlags.woff2";

// Windows omits country-flag glyphs from its emoji font, so flag emoji render as
// bare letters (e.g. "CZ") there. This injects a small, flags-only web font
// (self-hosted via webpack, no CDN) but only on browsers that support emoji yet
// lack flags — macOS/iOS/Android keep their own native flags untouched. The font
// is wired into the body font-family stack in styles.css.
polyfillCountryFlagEmojis("Twemoji Country Flags", flagFontUrl);
