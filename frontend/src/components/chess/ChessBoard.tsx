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

function ChessPiece({ piece, label }: ChessPieceProps) {
  const isWhite = piece === piece.toUpperCase();
  const role = piece.toLowerCase() as Lowercase<ChessPieceCode>;
  const className = `chess-piece ${isWhite ? "is-white-piece" : "is-black-piece"}`;

  return (
    <svg className={className} viewBox="0 0 64 64" role="img" aria-label={label} focusable="false">
      <PieceShape role={role} />
    </svg>
  );
}

function PieceShape({ role }: { role: Lowercase<ChessPieceCode> }) {
  if (role === "p") {
    return (
      <>
        <circle className="piece-fill" cx="32" cy="18" r="9" />
        <path className="piece-fill" d="M23 30c0-6 18-6 18 0l4 17H19z" />
        <path className="piece-fill" d="M17 51h30v7H17z" />
        <path className="piece-stroke" d="M32 9a9 9 0 0 1 0 18m-9 3c0-6 18-6 18 0l4 17H19zm-6 21h30v7H17z" />
      </>
    );
  }

  if (role === "r") {
    return (
      <>
        <path className="piece-fill" d="M16 13h8v7h5v-7h6v7h5v-7h8v16H16zM22 29h20v20H22zM16 49h32v9H16z" />
        <path className="piece-stroke" d="M16 13h8v7h5v-7h6v7h5v-7h8v16H16zm6 16h20v20H22zM16 49h32v9H16z" />
      </>
    );
  }

  if (role === "n") {
    return (
      <>
        <path className="piece-fill" d="M20 54h30c-3-10-11-16-21-18 3-6 8-9 13-11-4-9-13-13-24-12 6 5 5 10 1 16-4 6-3 16 1 25z" />
        <path className="piece-detail" d="M30 18c5 1 8 3 10 7M24 27l7 2" />
        <circle className="piece-detail-fill" cx="33" cy="22" r="1.8" />
        <path className="piece-stroke" d="M20 54h30c-3-10-11-16-21-18 3-6 8-9 13-11-4-9-13-13-24-12 6 5 5 10 1 16-4 6-3 16 1 25z" />
      </>
    );
  }

  if (role === "b") {
    return (
      <>
        <path className="piece-fill" d="M32 8c9 8 12 15 5 23l7 17H20l7-17C20 23 23 16 32 8zM18 50h28v8H18z" />
        <path className="piece-detail" d="M36 16 27 31" />
        <path className="piece-stroke" d="M32 8c9 8 12 15 5 23l7 17H20l7-17C20 23 23 16 32 8zM18 50h28v8H18z" />
      </>
    );
  }

  if (role === "q") {
    return (
      <>
        <path className="piece-fill" d="m15 49 4-25 8 12 5-19 5 19 8-12 4 25zM17 51h30v7H17z" />
        <circle className="piece-fill" cx="19" cy="21" r="5" />
        <circle className="piece-fill" cx="32" cy="14" r="5" />
        <circle className="piece-fill" cx="45" cy="21" r="5" />
        <path className="piece-stroke" d="m15 49 4-25 8 12 5-19 5 19 8-12 4 25zM17 51h30v7H17z" />
      </>
    );
  }

  return (
    <>
      <path className="piece-fill" d="M29 9h6v8h8v6h-8v10h11l-5 16H23l-5-16h11V23h-8v-6h8zM17 51h30v7H17z" />
      <path className="piece-stroke" d="M29 9h6v8h8v6h-8v10h11l-5 16H23l-5-16h11V23h-8v-6h8zM17 51h30v7H17z" />
    </>
  );
}
