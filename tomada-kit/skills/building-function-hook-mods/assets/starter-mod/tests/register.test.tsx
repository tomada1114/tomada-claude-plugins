import { describe, expect, test, tier } from 'claude-code/testing'

tier('user')

// The hooks a test registers sit BENEATH the mod, where the rest of the world
// would be, and nothing is beneath them. An unanswered call throws, naming the
// event. So a passing test answers every `$` call the mod makes.

describe('register', () => {
  test('the band draws while Claude is working', async ($) => {
    const tree = await $.ui.render({
      surface: 'terminal',
      component: 'AbovePrompt',
      requestId: 'band',
      props: {
        hasSurvey: false,
        isWorking: true,
        maxRows: 10,
        bodyColumns: 80,
        scroll: {} as never,
        view: {} as never,
      },
    })

    expect(JSON.stringify(tree)).toContain('hello from above the prompt')
  })

  test('the band stays out of the way when the turn is done', async ($, on) => {
    on('ui.render', { component: 'AbovePrompt' }, ($, e) => {
      const { Text } = $.ui.resolve(e)
      return <Text>BENEATH</Text>
    })

    const tree = await $.ui.render({
      surface: 'terminal',
      component: 'AbovePrompt',
      requestId: 'band',
      props: {
        hasSurvey: false,
        isWorking: false,
        maxRows: 10,
        bodyColumns: 80,
        scroll: {} as never,
        view: {} as never,
      },
    })

    // Our guard fell through to next(e), so what was beneath is what drew.
    expect(JSON.stringify(tree)).toContain('BENEATH')
  })
})
