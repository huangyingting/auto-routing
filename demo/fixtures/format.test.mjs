import assert from "node:assert/strict";
import test from "node:test";
import { greetingFormatter } from "./format.mjs";

test("trims standard spaces", () => {
  assert.equal(greetingFormatter("  Ada  "), "Hello, Ada!");
});

test("trims tabs and Unicode non-breaking spaces", () => {
  assert.equal(greetingFormatter("\t\u00A0Grace Hopper\u00A0\t"), "Hello, Grace Hopper!");
});

test("falls back to guest when blank", () => {
  assert.equal(greetingFormatter(" \t\u00A0 "), "Hello, guest!");
});
