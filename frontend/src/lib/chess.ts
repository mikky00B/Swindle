export type BoardSquare = {
  square: string;
  piece: ChessPieceCode | null;
  pieceName: string | null;
  isLight: boolean;
};

export type ChessPieceCode = "p" | "r" | "n" | "b" | "q" | "k" | "P" | "R" | "N" | "B" | "Q" | "K";

export const CHESS_PIECE_NAMES: Record<ChessPieceCode, string> = {
  p: "black pawn",
  r: "black rook",
  n: "black knight",
  b: "black bishop",
  q: "black queen",
  k: "black king",
  P: "white pawn",
  R: "white rook",
  N: "white knight",
  B: "white bishop",
  Q: "white queen",
  K: "white king",
};

export type BoardOrientation = "white" | "black";
export type BoardFile = "a" | "b" | "c" | "d" | "e" | "f" | "g" | "h";
export type BoardRank = 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8;
export type BoardCoordinates = {
  ranks: BoardRank[];
  files: BoardFile[];
};

const WHITE_COORDINATES: BoardCoordinates = {
  ranks: [8, 7, 6, 5, 4, 3, 2, 1],
  files: ["a", "b", "c", "d", "e", "f", "g", "h"],
};

const BLACK_COORDINATES: BoardCoordinates = {
  ranks: [1, 2, 3, 4, 5, 6, 7, 8],
  files: ["h", "g", "f", "e", "d", "c", "b", "a"],
};

const FILES: BoardFile[] = ["a", "b", "c", "d", "e", "f", "g", "h"];
const RANKS_DESC: BoardRank[] = [8, 7, 6, 5, 4, 3, 2, 1];

export function getBoardOrientation(userColor?: string | null): BoardOrientation {
  return userColor?.toLowerCase() === "black" ? "black" : "white";
}

export function getBoardCoordinates(orientation: BoardOrientation): BoardCoordinates {
  return orientation === "black" ? BLACK_COORDINATES : WHITE_COORDINATES;
}

export function fenToSquares(fen: string, orientation: BoardOrientation = "white"): BoardSquare[] {
  const board = parseFenBoard(fen);
  const coordinates = getBoardCoordinates(orientation);

  return coordinates.ranks.flatMap((rank) =>
    coordinates.files.map((file) => {
      const fileIndex = FILES.indexOf(file);
      const square = `${file}${rank}`;
      const piece = board[square] ?? null;
      return {
        square,
        piece,
        pieceName: piece ? CHESS_PIECE_NAMES[piece] : null,
        isLight: (fileIndex + rank) % 2 === 1,
      };
    }),
  );
}

export function parseFenBoard(fen: string): Record<string, ChessPieceCode | null> {
  const placement = fen.split(" ")[0];
  const rows = placement.split("/");
  const board: Record<string, ChessPieceCode | null> = {};

  rows.forEach((row, rowIndex) => {
    const rank = RANKS_DESC[rowIndex];
    if (!rank) {
      return;
    }
    let fileIndex = 0;

    for (const char of row) {
      const empty = Number(char);
      if (Number.isInteger(empty) && empty > 0) {
        for (let i = 0; i < empty; i += 1) {
          const file = FILES[fileIndex];
          if (file) {
            board[`${file}${rank}`] = null;
          }
          fileIndex += 1;
        }
      } else {
        const file = FILES[fileIndex];
        if (file) {
          board[`${file}${rank}`] = isPieceCode(char) ? char : null;
        }
        fileIndex += 1;
      }
    }
  });

  return board;
}

function isPieceCode(value: string): value is ChessPieceCode {
  return value in CHESS_PIECE_NAMES;
}
