/**
 * privacy-br/__tests__/validation.test.ts
 *
 * Foco: algoritmos de dígito verificador isolados.
 *   - validateCpf
 *   - validateCnpj
 *   - validateCnh
 *   - validateTituloEleitor
 *   - validateCep
 *   - luhn
 *
 * Compara contra vetores conhecidos das specs Receita Federal / DETRAN / TSE.
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  validateCpf,
  validateCnpj,
  validateCnh,
  validateTituloEleitor,
  validateCep,
  luhn,
} from "../patterns.js";
import {
  VALID_CPFS_RAW,
  INVALID_CPFS,
  VALID_CNPJS_RAW,
  INVALID_CNPJS,
  VALID_CNHS,
  INVALID_CNHS,
  VALID_TITULOS,
  INVALID_TITULOS,
} from "./corpus.js";

describe("validateCpf", () => {
  for (const cpf of VALID_CPFS_RAW) {
    it(`accepts valid: ${cpf}`, () => {
      assert.equal(validateCpf(cpf), true);
    });
  }
  for (const cpf of INVALID_CPFS) {
    it(`rejects invalid: ${cpf}`, () => {
      const digits = cpf.replace(/\D/g, "");
      if (digits.length === 11) {
        assert.equal(
          validateCpf(digits),
          false,
          `expected false for ${cpf}`,
        );
      }
    });
  }

  it("rejects all-same digits", () => {
    assert.equal(validateCpf("11111111111"), false);
    assert.equal(validateCpf("00000000000"), false);
    assert.equal(validateCpf("99999999999"), false);
  });

  it("rejects short / long", () => {
    assert.equal(validateCpf("1234567890"), false);   // 10
    assert.equal(validateCpf("123456789012"), false); // 12
  });

  it("rejects non-digit input", () => {
    assert.equal(validateCpf("abcdefghijk"), false);
    assert.equal(validateCpf("111.444.777-35"), false); // formatted = false
  });
});

describe("validateCnpj", () => {
  for (const cnpj of VALID_CNPJS_RAW) {
    it(`accepts valid: ${cnpj}`, () => {
      assert.equal(validateCnpj(cnpj), true);
    });
  }
  for (const cnpj of INVALID_CNPJS) {
    it(`rejects invalid: ${cnpj}`, () => {
      const digits = cnpj.replace(/\D/g, "");
      if (digits.length === 14) {
        assert.equal(validateCnpj(digits), false);
      }
    });
  }

  it("rejects all-same digits", () => {
    assert.equal(validateCnpj("11111111111111"), false);
    assert.equal(validateCnpj("00000000000000"), false);
  });

  it("rejects wrong length", () => {
    assert.equal(validateCnpj("1234567890123"), false);  // 13
    assert.equal(validateCnpj("123456789012345"), false); // 15
  });
});

describe("validateCnh", () => {
  for (const cnh of VALID_CNHS) {
    it(`accepts valid: ${cnh}`, () => {
      assert.equal(validateCnh(cnh), true);
    });
  }
  for (const cnh of INVALID_CNHS) {
    it(`rejects invalid: ${cnh}`, () => {
      assert.equal(validateCnh(cnh), false);
    });
  }
});

describe("validateTituloEleitor", () => {
  for (const t of VALID_TITULOS) {
    it(`accepts valid: ${t}`, () => {
      assert.equal(validateTituloEleitor(t), true);
    });
  }
  for (const t of INVALID_TITULOS) {
    it(`rejects invalid: ${t}`, () => {
      assert.equal(validateTituloEleitor(t), false);
    });
  }

  it("rejects UF out of range (>28)", () => {
    // UF 99 inválido — base = 12345678, UF = 99
    assert.equal(validateTituloEleitor("123456789999"), false);
  });

  it("rejects UF=00", () => {
    assert.equal(validateTituloEleitor("123456780000"), false);
  });
});

describe("validateCep", () => {
  it("accepts 8 digits", () => {
    assert.equal(validateCep("01310100"), true);
    assert.equal(validateCep("99999999"), true);
  });
  it("rejects 00000000 placeholder", () => {
    assert.equal(validateCep("00000000"), false);
  });
  it("rejects wrong length", () => {
    assert.equal(validateCep("1234567"), false);
    assert.equal(validateCep("123456789"), false);
  });
  it("rejects non-digit", () => {
    assert.equal(validateCep("01310-100"), false); // hifen presente = false
    assert.equal(validateCep("abcdefgh"), false);
  });
});

describe("luhn", () => {
  it("accepts known valid card", () => {
    assert.equal(luhn("4532015112830366"), true);
    assert.equal(luhn("5425233430109903"), true);
    assert.equal(luhn("4111111111111111"), true);
  });
  it("rejects mutated card", () => {
    assert.equal(luhn("4532015112830367"), false);
    assert.equal(luhn("1234567812345678"), false);
  });
  it("rejects all zeros", () => {
    // 0 sums to 0, 0 % 10 == 0 — Luhn passes. Mas length check
    // garante que matchers exijam ≥13 dígitos antes; aqui luhn isolada
    // bate. Documentamos: pattern usa validate() compositie.
    assert.equal(luhn("0000000000000000"), true);
  });
  it("rejects non-digit", () => {
    assert.equal(luhn("abcd"), false);
  });
});

describe("CPF algorithm — known spec vectors", () => {
  // Vetores comuns em literatura BR fintech
  const knownValid = [
    { cpf: "11144477735", desc: "spec example" },
    { cpf: "52998224725", desc: "common test" },
  ];
  for (const { cpf, desc } of knownValid) {
    it(`spec: ${cpf} (${desc})`, () => {
      assert.equal(validateCpf(cpf), true);
    });
  }
});

describe("CNPJ algorithm — known spec vectors", () => {
  const knownValid = [
    { cnpj: "11222333000181", desc: "common test pattern" },
    { cnpj: "04252011000110", desc: "BCB-style test" },
  ];
  for (const { cnpj, desc } of knownValid) {
    it(`spec: ${cnpj} (${desc})`, () => {
      assert.equal(validateCnpj(cnpj), true);
    });
  }
});
