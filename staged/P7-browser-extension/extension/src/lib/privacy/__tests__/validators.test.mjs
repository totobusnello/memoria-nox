/**
 * validators.test.mjs — Tests for CPF/CNPJ/Luhn/CEP/CNH/Título de Eleitor.
 *
 * Uses node:test (no external runner). Run with `node --test`.
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import {
  validateCpf,
  validateCnpj,
  validateCep,
  validateCnh,
  validateTituloEleitor,
  luhn,
  digitsOnly,
} from "../validators.js";

// ─── CPF ──────────────────────────────────────────────────────────────────────

test("validateCpf — accepts known-valid digits", () => {
  // Test CPFs (synthetic, generated with valid check digits):
  assert.equal(validateCpf("12345678909"), true);
  assert.equal(validateCpf("11144477735"), true);
});

test("validateCpf — rejects 11 identical digits (placeholders)", () => {
  for (let i = 0; i < 10; i++) {
    assert.equal(validateCpf(String(i).repeat(11)), false, `digit ${i}`);
  }
});

test("validateCpf — rejects wrong length / non-digits", () => {
  assert.equal(validateCpf(""), false);
  assert.equal(validateCpf("123"), false);
  assert.equal(validateCpf("12345678901234"), false);
  assert.equal(validateCpf("123.456.789-09"), false); // formatted, must normalize first
});

test("validateCpf — rejects when check digit fails", () => {
  // Change last digit
  assert.equal(validateCpf("12345678900"), false);
  assert.equal(validateCpf("12345678901"), false);
});

// ─── CNPJ ─────────────────────────────────────────────────────────────────────

test("validateCnpj — accepts known-valid", () => {
  // 11.222.333/0001-81  and  04.252.011/0001-10 (synthetic)
  assert.equal(validateCnpj("11222333000181"), true);
  assert.equal(validateCnpj("04252011000110"), true);
});

test("validateCnpj — rejects 14 identical digits", () => {
  for (let i = 0; i < 10; i++) {
    assert.equal(validateCnpj(String(i).repeat(14)), false);
  }
});

test("validateCnpj — rejects malformed", () => {
  assert.equal(validateCnpj(""), false);
  assert.equal(validateCnpj("12345"), false);
  assert.equal(validateCnpj("11.222.333/0001-81"), false); // formatted
});

// ─── Luhn ────────────────────────────────────────────────────────────────────

test("luhn — accepts known-valid card numbers", () => {
  assert.equal(luhn("4532015112830366"), true);
  assert.equal(luhn("5425233430109903"), true);
  // 13-digit Visa
  assert.equal(luhn("4222222222222"), true);
});

test("luhn — rejects sequences that don't sum to mod 10", () => {
  assert.equal(luhn("4532015112830367"), false);
  assert.equal(luhn("1234567890123456"), false);
});

test("luhn — rejects non-digits", () => {
  assert.equal(luhn(""), false);
  assert.equal(luhn("abc"), false);
  assert.equal(luhn("4532 0151 1283 0366"), false); // must be pre-normalized
});

// ─── CEP ─────────────────────────────────────────────────────────────────────

test("validateCep — accepts 8 digits", () => {
  assert.equal(validateCep("01310100"), true);
  assert.equal(validateCep("04567890"), true);
});

test("validateCep — rejects placeholder 00000000", () => {
  assert.equal(validateCep("00000000"), false);
});

test("validateCep — rejects wrong length", () => {
  assert.equal(validateCep("0131010"), false);
  assert.equal(validateCep("013101000"), false);
  assert.equal(validateCep(""), false);
});

// ─── CNH ─────────────────────────────────────────────────────────────────────

test("validateCnh — rejects 11 identical digits", () => {
  for (let i = 0; i < 10; i++) {
    assert.equal(validateCnh(String(i).repeat(11)), false);
  }
});

test("validateCnh — rejects wrong length", () => {
  assert.equal(validateCnh(""), false);
  assert.equal(validateCnh("1234567"), false);
  assert.equal(validateCnh("123456789012"), false);
});

// ─── Título de Eleitor ──────────────────────────────────────────────────────

test("validateTituloEleitor — UF out of range rejected", () => {
  // UF = 99 (invalid)
  assert.equal(validateTituloEleitor("123456789912"), false);
  // UF = 00 (invalid)
  assert.equal(validateTituloEleitor("123456780012"), false);
});

test("validateTituloEleitor — rejects 12 identical digits", () => {
  assert.equal(validateTituloEleitor("111111111111"), false);
});

test("validateTituloEleitor — rejects wrong length", () => {
  assert.equal(validateTituloEleitor(""), false);
  assert.equal(validateTituloEleitor("12345"), false);
});

// ─── digitsOnly ─────────────────────────────────────────────────────────────

test("digitsOnly — strips non-digits", () => {
  assert.equal(digitsOnly("123.456.789-09"), "12345678909");
  assert.equal(digitsOnly("+55 11 99999-9999"), "5511999999999");
  assert.equal(digitsOnly("abc"), "");
  assert.equal(digitsOnly(""), "");
});
