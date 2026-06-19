import { type ChessPieceCode, fenToSquares, getBoardOrientation } from "../../lib/chess";

type ChessBoardProps = {
  fen?: string | null;
  from?: string | null;
  to?: string | null;
  orientation?: "white" | "black" | null;
};

const STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";

export function ChessBoard({ fen, from, to, orientation }: ChessBoardProps) {
  const squares = fenToSquares(fen || STARTING_FEN, getBoardOrientation(orientation));

  return (
    <div className="board" aria-label="Key chess position">
      {squares.map((square) => {
        const isFrom = square.square === from;
        const isTo = square.square === to;
        return (
          <div
            className={[
              "board-square",
              square.isLight ? "is-light" : "is-dark",
              isFrom ? "is-from" : "",
              isTo ? "is-to" : "",
            ].join(" ")}
            key={square.square}
          >
            {square.piece ? <ChessPiece piece={square.piece} label={square.pieceName ?? "chess piece"} /> : null}
          </div>
        );
      })}
    </div>
  );
}

type ChessPieceProps = {
  piece: ChessPieceCode;
  label: string;
};

type PiecePalette = {
  fill: string;
  outline: string;
};

const PIECE_PALETTES: Record<"white" | "black", PiecePalette> = {
  white: {
    fill: "#fbfaf2",
    outline: "#1e261f",
  },
  black: {
    fill: "#202820",
    outline: "#f4efd9",
  },
};

function ChessPiece({ piece, label }: ChessPieceProps) {
  const isWhite = piece === piece.toUpperCase();
  const role = piece.toLowerCase() as Lowercase<ChessPieceCode>;
  const className = `chess-piece ${isWhite ? "is-white-piece" : "is-black-piece"}`;
  const palette = isWhite ? PIECE_PALETTES.white : PIECE_PALETTES.black;

  return (
    <svg className={className} viewBox="0 0 64 64" role="img" aria-label={label} focusable="false">
      <PieceShape role={role} palette={palette} />
    </svg>
  );
}

function PieceShape({ role, palette }: { role: Lowercase<ChessPieceCode>; palette: PiecePalette }) {
  const fillProps = {
    fill: palette.fill,
    stroke: palette.outline,
    strokeWidth: 2.4,
    strokeLinejoin: "round",
    strokeLinecap: "round",
  } as const;
  const strokeProps = {
    fill: "none",
    stroke: palette.outline,
    strokeWidth: 2.4,
    strokeLinecap: "round",
    strokeLinejoin: "round",
  } as const;

  if (role === "p") {
    return (
      <>
        <circle {...fillProps} cx="32" cy="18" r="9" />
        <path {...fillProps} d="M23 30c0-6 18-6 18 0l4 17H19z" />
        <path {...fillProps} d="M17 51h30v7H17z" />
        <path {...strokeProps} d="M32 9a9 9 0 0 1 0 18m-9 3c0-6 18-6 18 0l4 17H19zm-6 21h30v7H17z" />
      </>
    );
  }

  if (role === "r") {
    return (
      <>
        <path {...fillProps} d="M16 13h8v7h5v-7h6v7h5v-7h8v16H16zM22 29h20v20H22zM16 49h32v9H16z" />
        <path {...strokeProps} d="M16 13h8v7h5v-7h6v7h5v-7h8v16H16zm6 16h20v20H22zM16 49h32v9H16z" />
      </>
    );
  }

  if (role === "n") {
    return (
      <>
        <path {...fillProps} d="M20 54h30c-3-10-11-16-21-18 3-6 8-9 13-11-4-9-13-13-24-12 6 5 5 10 1 16-4 6-3 16 1 25z" />
        <path {...strokeProps} d="M30 18c5 1 8 3 10 7M24 27l7 2" />
        <circle fill={palette.outline} cx="33" cy="22" r="1.8" />
        <path {...strokeProps} d="M20 54h30c-3-10-11-16-21-18 3-6 8-9 13-11-4-9-13-13-24-12 6 5 5 10 1 16-4 6-3 16 1 25z" />
      </>
    );
  }

  if (role === "b") {
    return (
      <>
        <path {...fillProps} d="M32 8c9 8 12 15 5 23l7 17H20l7-17C20 23 23 16 32 8zM18 50h28v8H18z" />
        <path {...strokeProps} d="M36 16 27 31" />
        <path {...strokeProps} d="M32 8c9 8 12 15 5 23l7 17H20l7-17C20 23 23 16 32 8zM18 50h28v8H18z" />
      </>
    );
  }

  if (role === "q") {
    return (
      <>
        <path {...fillProps} d="m15 49 4-25 8 12 5-19 5 19 8-12 4 25zM17 51h30v7H17z" />
        <circle {...fillProps} cx="19" cy="21" r="5" />
        <circle {...fillProps} cx="32" cy="14" r="5" />
        <circle {...fillProps} cx="45" cy="21" r="5" />
        <path {...strokeProps} d="m15 49 4-25 8 12 5-19 5 19 8-12 4 25zM17 51h30v7H17z" />
      </>
    );
  }

  return (
    <>
      <path {...fillProps} d="M29 9h6v8h8v6h-8v10h11l-5 16H23l-5-16h11V23h-8v-6h8zM17 51h30v7H17z" />
      <path {...strokeProps} d="M29 9h6v8h8v6h-8v10h11l-5 16H23l-5-16h11V23h-8v-6h8zM17 51h30v7H17z" />
    </>
  );
}
