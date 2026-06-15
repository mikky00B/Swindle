import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import {
  CHESS_PIECE_NAMES,
  fenToSquares,
  getBoardCoordinates,
  getBoardOrientation,
  parseFenBoard,
} from "../src/lib/chess.ts";
import { positionLabel } from "../src/lib/boardLabels.ts";
import { getMetricRows } from "../src/lib/cardMetrics.ts";
import { MOCK_CARD } from "../src/mockData.ts";

const CORNER_FEN = "r6k/8/8/8/8/8/8/R6K w - - 0 1";
const CROWDED_FEN = "r3k2r/pppq1ppp/2npbn2/3Np3/2B1P3/2NP1Q2/PPP2PPP/R3K2R w KQkq - 0 1";
const REAL_IMPORTED_FINAL_FEN = "r2q1rk1/pp2bppp/2n1pn2/2bp4/3P4/2PBPN2/PP1N1PPP/R1BQ1RK1 w - - 0 9";
const REAL_WHITE_GAME_FINAL_FEN = "r5rk/p1p5/1p1pNn1p/3P1p2/2P1p3/6bq/PPBQ1P2/R4RK1 w - - 0 25";
const REAL_BLACK_GAME_FINAL_FEN = "r1b1k2r/5p1p/p2qp1p1/1p3n2/8/3QB2P/PbB2PP1/RN3RK1 w kq - 0 19";

function signature(fen: string, orientation: "white" | "black"): string[] {
  return fenToSquares(fen, orientation).map((square) => `${square.square}:${square.piece ?? "."}`);
}

{
  assert.deepEqual(getBoardCoordinates("white"), {
    ranks: [8, 7, 6, 5, 4, 3, 2, 1],
    files: ["a", "b", "c", "d", "e", "f", "g", "h"],
  });
  assert.deepEqual(getBoardCoordinates("black"), {
    ranks: [1, 2, 3, 4, 5, 6, 7, 8],
    files: ["h", "g", "f", "e", "d", "c", "b", "a"],
  });
  assert.equal(getBoardOrientation("white"), "white");
  assert.equal(getBoardOrientation("black"), "black");
  assert.equal(getBoardOrientation(null), "white");
}

{
  const squares = fenToSquares("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", "white");

  assert.equal(squares[0].square, "a8");
  assert.equal(squares[0].piece, "r");
  assert.equal(squares[63].square, "h1");
  assert.equal(squares[63].piece, "R");
}

{
  const squares = fenToSquares("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", "black");

  assert.equal(squares[0].square, "h1");
  assert.equal(squares[0].piece, "R");
  assert.equal(squares[63].square, "a8");
  assert.equal(squares[63].piece, "r");
}

{
  const squares = fenToSquares("8/8/8/8/8/8/4k3/4K3 w - - 0 1", "white");

  assert.equal(squares.length, 64);
  assert.equal(squares.filter((square) => square.piece === null).length, 62);
  assert.equal(squares.find((square) => square.square === "e2")?.piece, "k");
  assert.equal(squares.find((square) => square.square === "e1")?.piece, "K");
  assert.equal(squares[60].square, "e1");
  assert.equal(squares[52].square, "e2");
}

{
  const squares = fenToSquares("8/8/8/8/8/8/4k3/4K3 b - - 0 1", "white");

  assert.equal(squares.find((square) => square.square === "e2")?.piece, "k");
  assert.equal(squares.find((square) => square.square === "e1")?.piece, "K");
}

{
  const squares = fenToSquares("8/8/8/8/8/8/4k3/4K3 w - - 0 1", "black");

  assert.equal(squares[3].square, "e1");
  assert.equal(squares[3].piece, "K");
  assert.equal(squares[11].square, "e2");
  assert.equal(squares[11].piece, "k");
}

{
  const squares = fenToSquares(CORNER_FEN, "white");

  assert.deepEqual(
    [squares[0], squares[7], squares[56], squares[63]].map((square) => [square.square, square.piece]),
    [
      ["a8", "r"],
      ["h8", "k"],
      ["a1", "R"],
      ["h1", "K"],
    ],
  );
}

{
  const squares = fenToSquares(CORNER_FEN, "black");

  assert.deepEqual(
    [squares[0], squares[7], squares[56], squares[63]].map((square) => [square.square, square.piece]),
    [
      ["h1", "K"],
      ["a1", "R"],
      ["h8", "k"],
      ["a8", "r"],
    ],
  );
}

{
  assert.deepEqual(signature(CROWDED_FEN, "white"), [
    "a8:r",
    "b8:.",
    "c8:.",
    "d8:.",
    "e8:k",
    "f8:.",
    "g8:.",
    "h8:r",
    "a7:p",
    "b7:p",
    "c7:p",
    "d7:q",
    "e7:.",
    "f7:p",
    "g7:p",
    "h7:p",
    "a6:.",
    "b6:.",
    "c6:n",
    "d6:p",
    "e6:b",
    "f6:n",
    "g6:.",
    "h6:.",
    "a5:.",
    "b5:.",
    "c5:.",
    "d5:N",
    "e5:p",
    "f5:.",
    "g5:.",
    "h5:.",
    "a4:.",
    "b4:.",
    "c4:B",
    "d4:.",
    "e4:P",
    "f4:.",
    "g4:.",
    "h4:.",
    "a3:.",
    "b3:.",
    "c3:N",
    "d3:P",
    "e3:.",
    "f3:Q",
    "g3:.",
    "h3:.",
    "a2:P",
    "b2:P",
    "c2:P",
    "d2:.",
    "e2:.",
    "f2:P",
    "g2:P",
    "h2:P",
    "a1:R",
    "b1:.",
    "c1:.",
    "d1:.",
    "e1:K",
    "f1:.",
    "g1:.",
    "h1:R",
  ]);

  assert.deepEqual(signature(CROWDED_FEN, "black"), [
    "h1:R",
    "g1:.",
    "f1:.",
    "e1:K",
    "d1:.",
    "c1:.",
    "b1:.",
    "a1:R",
    "h2:P",
    "g2:P",
    "f2:P",
    "e2:.",
    "d2:.",
    "c2:P",
    "b2:P",
    "a2:P",
    "h3:.",
    "g3:.",
    "f3:Q",
    "e3:.",
    "d3:P",
    "c3:N",
    "b3:.",
    "a3:.",
    "h4:.",
    "g4:.",
    "f4:.",
    "e4:P",
    "d4:.",
    "c4:B",
    "b4:.",
    "a4:.",
    "h5:.",
    "g5:.",
    "f5:.",
    "e5:p",
    "d5:N",
    "c5:.",
    "b5:.",
    "a5:.",
    "h6:.",
    "g6:.",
    "f6:n",
    "e6:b",
    "d6:p",
    "c6:n",
    "b6:.",
    "a6:.",
    "h7:p",
    "g7:p",
    "f7:p",
    "e7:.",
    "d7:q",
    "c7:p",
    "b7:p",
    "a7:p",
    "h8:r",
    "g8:.",
    "f8:.",
    "e8:k",
    "d8:.",
    "c8:.",
    "b8:.",
    "a8:r",
  ]);
}

{
  assert.deepEqual(Object.keys(CHESS_PIECE_NAMES).sort(), ["B", "K", "N", "P", "Q", "R", "b", "k", "n", "p", "q", "r"]);
  assert.equal(CHESS_PIECE_NAMES.p, "black pawn");
  assert.equal(CHESS_PIECE_NAMES.r, "black rook");
  assert.equal(CHESS_PIECE_NAMES.n, "black knight");
  assert.equal(CHESS_PIECE_NAMES.b, "black bishop");
  assert.equal(CHESS_PIECE_NAMES.q, "black queen");
  assert.equal(CHESS_PIECE_NAMES.k, "black king");
  assert.equal(CHESS_PIECE_NAMES.P, "white pawn");
  assert.equal(CHESS_PIECE_NAMES.R, "white rook");
  assert.equal(CHESS_PIECE_NAMES.N, "white knight");
  assert.equal(CHESS_PIECE_NAMES.B, "white bishop");
  assert.equal(CHESS_PIECE_NAMES.Q, "white queen");
  assert.equal(CHESS_PIECE_NAMES.K, "white king");
}

{
  const board = parseFenBoard(REAL_IMPORTED_FINAL_FEN);

  assert.equal(board.a8, "r");
  assert.equal(board.d8, "q");
  assert.equal(board.f8, "r");
  assert.equal(board.g8, "k");
  assert.equal(board.c6, "n");
  assert.equal(board.f6, "n");
  assert.equal(board.c5, "b");
  assert.equal(board.d4, "P");
  assert.equal(board.c3, "P");
  assert.equal(board.d3, "B");
  assert.equal(board.e3, "P");
  assert.equal(board.f3, "N");
  assert.equal(board.a1, "R");
  assert.equal(board.c1, "B");
  assert.equal(board.d1, "Q");
  assert.equal(board.f1, "R");
  assert.equal(board.g1, "K");
  assert.equal(board.h1, null);
}

{
  const whiteImportedCard = {
    ...MOCK_CARD,
    game: { ...MOCK_CARD.game, user_color: "white" as const, final_fen: REAL_IMPORTED_FINAL_FEN },
    story: { ...MOCK_CARD.story, key_position_fen: REAL_IMPORTED_FINAL_FEN },
  };
  const blackImportedCard = {
    ...MOCK_CARD,
    game: { ...MOCK_CARD.game, user_color: "black" as const, final_fen: REAL_IMPORTED_FINAL_FEN },
    story: { ...MOCK_CARD.story, key_position_fen: REAL_IMPORTED_FINAL_FEN },
  };

  const whiteSquares = fenToSquares(whiteImportedCard.story.key_position_fen, getBoardOrientation(whiteImportedCard.game.user_color));
  const blackSquares = fenToSquares(blackImportedCard.story.key_position_fen, getBoardOrientation(blackImportedCard.game.user_color));

  assert.equal(whiteSquares[0].square, "a8");
  assert.equal(whiteSquares[0].piece, "r");
  assert.equal(whiteSquares[63].square, "h1");
  assert.equal(whiteSquares[63].piece, null);
  assert.equal(blackSquares[0].square, "h1");
  assert.equal(blackSquares[0].piece, null);
  assert.equal(blackSquares[63].square, "a8");
  assert.equal(blackSquares[63].piece, "r");
  assert.equal(whiteSquares.find((square) => square.square === "g1")?.piece, "K");
  assert.equal(blackSquares[1].square, "g1");
  assert.equal(blackSquares[1].piece, "K");
  assert.equal(blackSquares[57].square, "g8");
  assert.equal(blackSquares[57].piece, "k");
}

{
  const realWhiteGameSquares = fenToSquares(REAL_WHITE_GAME_FINAL_FEN, getBoardOrientation("white"));

  assert.equal(realWhiteGameSquares[0].square, "a8");
  assert.equal(realWhiteGameSquares[0].piece, "r");
  assert.equal(realWhiteGameSquares[7].square, "h8");
  assert.equal(realWhiteGameSquares[7].piece, "k");
  assert.equal(realWhiteGameSquares[56].square, "a1");
  assert.equal(realWhiteGameSquares[56].piece, "R");
  assert.equal(realWhiteGameSquares[62].square, "g1");
  assert.equal(realWhiteGameSquares[62].piece, "K");
  assert.equal(realWhiteGameSquares.find((square) => square.square === "e6")?.piece, "N");
  assert.equal(realWhiteGameSquares.find((square) => square.square === "h3")?.piece, "q");
}

{
  const realBlackGameSquares = fenToSquares(REAL_BLACK_GAME_FINAL_FEN, getBoardOrientation("black"));

  assert.equal(realBlackGameSquares[0].square, "h1");
  assert.equal(realBlackGameSquares[0].piece, null);
  assert.equal(realBlackGameSquares[1].square, "g1");
  assert.equal(realBlackGameSquares[1].piece, "K");
  assert.equal(realBlackGameSquares[7].square, "a1");
  assert.equal(realBlackGameSquares[7].piece, "R");
  assert.equal(realBlackGameSquares[56].square, "h8");
  assert.equal(realBlackGameSquares[56].piece, "r");
  assert.equal(realBlackGameSquares[60].square, "d8");
  assert.equal(realBlackGameSquares[60].piece, null);
  assert.equal(realBlackGameSquares[63].square, "a8");
  assert.equal(realBlackGameSquares[63].piece, "r");
  assert.equal(realBlackGameSquares.find((square) => square.square === "b2")?.piece, "b");
  assert.equal(realBlackGameSquares.find((square) => square.square === "d3")?.piece, "Q");
}

{
  assert.equal(positionLabel("final_position"), "Final position");
  assert.equal(positionLabel("key_position"), "Key position");
  assert.equal(positionLabel("fallback_starting_position"), "Starting position fallback");
}

{
  const rows = getMetricRows({
    ...MOCK_CARD,
    game: {
      ...MOCK_CARD.game,
      opponent_username: "Bai_Daniil",
      opponent_rating: 1096,
    },
    metrics: {},
  });

  assert.deepEqual(rows.find(([label]) => label === "Opponent"), ["Opponent", "Bai_Daniil"]);
  assert.deepEqual(rows.find(([label]) => label === "Opp. rating"), ["Opp. rating", "1096"]);
}

{
  const shareCardSource = readFileSync(new URL("../src/components/cards/ShareCard.tsx", import.meta.url), "utf8");
  const appSource = readFileSync(new URL("../src/App.tsx", import.meta.url), "utf8");

  assert.equal(shareCardSource.includes("board-debug"), false);
  assert.equal(shareCardSource.includes(" / {card.board_position_source}"), false);
  assert.equal(shareCardSource.includes("getBoardOrientation"), false);
  assert.equal(shareCardSource.includes('orientation === "black"'), false);
  assert.equal(shareCardSource.includes("<ChessBoard"), true);
  assert.ok((appSource.match(/<ShareCard\s/g) ?? []).length >= 2);
}

console.log("chess orientation tests passed");
