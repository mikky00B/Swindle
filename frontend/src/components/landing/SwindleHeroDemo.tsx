import { Badge, Bar, Button, Collapse, Row, Spinner, Stage, States, Text, Window, type Act } from '../../stageshow-kit'
import './swindle-hero.css'

// Swindle's hero: a game finishes processing in the journal, the story
// resolves onto the row, and the share card comes forward. Compact tells
// the same story smaller: the row carries the beat, the card is the
// bottom-bleed hero.

type S = {
  /** The newest row's story has resolved (badge + headline + action shown) */
  resolved: boolean
  /** The share card is up; the journal recedes behind it */
  card: boolean
}

const initial: S = { resolved: false, card: false }

const POSTER: S = { resolved: true, card: true }

const HEADLINE = 'Completely lost, somehow walked out with the full point.'

// The card's key position, from the story object (before Nxe5, f3 to e5).
const BOARD: string[][] = [
  ['r', '', '', 'q', '', 'r', 'k', ''],
  ['p', 'p', '', '', 'b', 'p', 'p', 'p'],
  ['', '', 'n', '', 'p', 'n', '', ''],
  ['', '', 'b', 'p', '', '', '', ''],
  ['', '', '', 'P', '', '', '', ''],
  ['', '', 'P', 'B', 'P', 'N', '', ''],
  ['P', 'P', '', 'N', '', 'P', 'P', 'P'],
  ['R', '', 'B', 'Q', '', 'R', 'K', ''],
]
const HIGHLIGHTS = new Set(['f3', 'e5'])
const FILES = 'abcdefgh'

const REST = { wide: { x: 54, y: 428 }, compact: { x: 40, y: 128 } }

async function script(a: Act<S>) {
  await a.wait(700)

  // The story resolves onto the newest row.
  await a.set({ resolved: true })
  await a.wait(900)

  // Open the card: its own button in wide, the row itself in compact.
  const open = a.layout === 'compact' ? 'story-row' : 'open-card'
  await a.move(open)
  await a.wait(250)
  await a.click()
  await a.set({ card: true })
  await a.wait(2600)

  // Put everything back, so the loop has no seam.
  await a.move('rest')
  await a.wait(300)
  await a.set({ card: false })
  await a.wait(500)
  await a.set({ resolved: false })
  await a.wait(700)
}

export function SwindleHeroDemo() {
  return (
    <Stage
      width={520}
      height={460}
      compact={{ below: 460, width: 358, height: 420 }}
      initial={initial}
      poster={POSTER}
      script={script}
      cursor={{ at: REST }}
      className="sw"
      accent="#17201b"
    >
      {(s, _rect, layout) => (
        <>
          <Window url="swindle.app/journal" className="sw-window">
            <div className="sw-app" data-card={s.card || undefined}>
              <header className="sw-header">
                <Text className="sw-title">Journal</Text>
                <Button size="small" data-target="export">
                  Export PNG
                </Button>
              </header>

              <div className="sw-rows">
                <Row
                  className="sw-row sw-row-lead"
                  title="vs PawnCrusher"
                  subtitle="Italian Game · Loss"
                  meta={<Badge tone="danger">Loss</Badge>}
                />
                <Row
                  className="sw-row"
                  title="vs nearPeer"
                  subtitle="Sicilian Defense · Win"
                  meta={<Badge tone="success">Win</Badge>}
                />

                {/* The story row: processing, then resolved */}
                <div className="sw-story" data-target="story-row" data-cursor="hand">
                  <Row
                    className="sw-row"
                    title={
                      layout === 'compact' ? (
                        <span className="sw-row-title">
                          vs higherRated
                          <span className={`sw-mini-badge${s.resolved ? ' is-on' : ''}`}>
                            The Swindle <span className="sw-badge-emoji">🪄</span>
                          </span>
                        </span>
                      ) : (
                        'vs higherRated'
                      )
                    }
                    subtitle="Blitz · 3+2"
                    meta={
                      <States
                        value={s.resolved ? 'win' : 'detecting'}
                        states={{
                          detecting: <Spinner />,
                          win: <Badge tone="success">Win</Badge>,
                        }}
                      />
                    }
                  />
                  <Collapse reveal="drop" open={s.resolved}>
                    <div className="sw-reveal">
                      <span className="sw-badge">
                        The Swindle <span className="sw-badge-emoji">🪄</span>
                      </span>
                      <p className="sw-headline">{HEADLINE}</p>
                      <Button size="small" variant="primary" data-target="open-card" data-cursor="hand">
                        Open card
                      </Button>
                    </div>
                  </Collapse>
                </div>

                {/* Filler rows below keep the list real */}
                <Row
                  className="sw-row sw-row-filler"
                  title={<Bar w={72} h={7} tone={2} />}
                  subtitle={<Bar w={52} h={6} tone={1} />}
                  meta={<Bar w={38} h={16} r={8} tone={1} />}
                />
              </div>
            </div>
          </Window>

          {/* The share card, the payoff */}
          <div className="sw-card" data-show={s.card}>
            <div className="sw-card-brand">
              <span className="sw-card-mark">♞</span>
              <span>Swindle</span>
              <strong>Daily story</strong>
            </div>
            <span className="sw-badge sw-badge--card">
              The Swindle <span className="sw-badge-emoji">🪄</span>
            </span>
            <p className="sw-card-headline">{HEADLINE}</p>
            <div className="sw-board" aria-hidden="true">
              {BOARD.map((rank, r) =>
                rank.map((piece, f) => {
                  const square = `${FILES[f]}${8 - r}`
                  const dark = (r + f) % 2 === 1
                  return (
                    <span
                      key={square}
                      className={`sw-square${dark ? ' is-dark' : ''}${HIGHLIGHTS.has(square) ? ' is-highlight' : ''}`}
                    >
                      {piece ? <span className={`sw-piece ${piece === piece.toUpperCase() ? 'is-white' : 'is-black'}`}>{glyph(piece)}</span> : null}
                    </span>
                  )
                }),
              )}
            </div>
            <div className="sw-card-meta">
              <span>Win · 48 moves</span>
              <strong>+14</strong>
            </div>
          </div>

          <span data-target="rest" style={{ position: 'absolute', left: REST[layout].x, top: REST[layout].y }} />
        </>
      )}
    </Stage>
  )
}

// One filled glyph per piece, colored per side by CSS.
function glyph(piece: string): string {
  const white = piece === piece.toUpperCase()
  const map: Record<string, string> = white
    ? { P: '♙', N: '♘', B: '♗', R: '♖', Q: '♕', K: '♔' }
    : { p: '♟', n: '♞', b: '♝', r: '♜', q: '♛', k: '♚' }
  return map[piece]
}
