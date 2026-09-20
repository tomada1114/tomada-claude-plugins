/* @jsx h */
/* @jsxFrag Fragment */

// Never name a local variable `h` in a file that uses JSX. `h` and `Fragment`
// are ambient globals the engine injects; every JSX tag compiles to a call of
// `h`, so a local `h` silently breaks every tag in the file.

import type { On } from 'claude-code'

export function register(on: On) {
  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    // Other surfaces draw their own band, and a survey owns the band when one
    // is up. `isWorking` is recomputed by the engine, so this single guard is
    // the whole show-while-working / hide-when-done behaviour — there is no
    // hide-on-complete code to write.
    if (e.surface !== 'terminal' || e.props.hasSurvey || !e.props.isWorking) {
      return next(e)
    }

    // Elements are never globals — they come from the surface's table.
    // `$.ui.resolve` is synchronous despite living on `$.ui`.
    const { Box, Text } = $.ui.resolve(e)

    const rows = Math.min(3, e.props.maxRows)

    return (
      <Box flexDirection="column" height={rows}>
        <Text color="magenta" bold>
          {'✦ '}
        </Text>
        <Text color="cyan">hello from above the prompt</Text>
      </Box>
    )
  })
}
