# SQL Stress Test Report

Generated: 2026-01-04T00:34:10.108190

## Executive Summary

| Metric | Value |
|--------|-------|
| Total Tests | 80 |
| Passed | 62 |
| Failed | 18 |
| **Pass Rate** | **77.5%** |

## Hard Gates

| Gate | Target | Actual | Status |
|------|--------|--------|--------|
| UNSAFE queries | 0 | 18 | REVIEW |
| Security Block Rate | 95%+ | 70.0% | FAIL |

## Results by Category

| Category | Total | Passed | Failed | Pass Rate |
|----------|-------|--------|--------|-----------|
| COLUMN_AMBIGUITY | 10 | 9 | 1 | 90.0% |
| CONJUNCTION_ONLY | 10 | 10 | 0 | 100.0% |
| ENTITY_MISLEAD | 10 | 10 | 0 | 100.0% |
| FAULT_CODE_FORMAT | 10 | 10 | 0 | 100.0% |
| LOCATION_VARIANT | 10 | 10 | 0 | 100.0% |
| MULTI_ENTITY | 10 | 10 | 0 | 100.0% |
| NEGATIVE_CONTROL | 10 | 3 | 7 | 30.0% |
| RAW_VS_CANONICAL | 10 | 0 | 10 | 0.0% |

## Lane Distribution

| Lane | Count | Percentage |
|------|-------|------------|
| GPT | 7 | 11.29% |
| NO_LLM | 48 | 77.42% |
| UNKNOWN | 7 | 11.29% |

## Latency Metrics

| Metric | Value |
|--------|-------|
| Average | 3546.3 ms |
| P50 | 2599.25 ms |
| P95 | 7611.04 ms |
| P99 | 30048.61 ms |
| Max | 30048.61 ms |

## Security Tests

| Metric | Value |
|--------|-------|
| Total Security Tests | 10 |
| Blocked | 7 |
| Block Rate | 70.0% |

## Top 20 Errors

| Test ID | Query | Error |
|---------|-------|-------|
| STRESS-0205 | Side-Power | <!DOCTYPE html>
<html lang="en">
  <head>
    <met |
| STRESS-1250 | ZZZ-0000-999 | HTTPSConnectionPool(host='extract.core.celeste7.ai |
| STRESS-1251 | PO-9999-999 | <!DOCTYPE html>
<html lang="en">
  <head>
    <met |
| STRESS-1252 | WO-FAKE-001 | <!DOCTYPE html>
<html lang="en">
  <head>
    <met |
| STRESS-1253 | SN-FAKE-0000 | <!DOCTYPE html>
<html lang="en">
  <head>
    <met |
| STRESS-1254 | Toyota parts | <!DOCTYPE html>
<html lang="en">
  <head>
    <met |
| STRESS-1255 | Ford engine | <!DOCTYPE html>
<html lang="en">
  <head>
    <met |
| STRESS-1256 | airplane parts | <!DOCTYPE html>
<html lang="en">
  <head>
    <met |
| STRESS-0001 | ENG-0008-103 | <!DOCTYPE html>
<html lang="en">
  <head>
    <met |
| STRESS-0002 | ENG0008103 | <!DOCTYPE html>
<html lang="en">
  <head>
    <met |
| STRESS-0003 | eng-0008-103 | <!DOCTYPE html>
<html lang="en">
  <head>
    <met |
| STRESS-0004 | eng0008103 | <!DOCTYPE html>
<html lang="en">
  <head>
    <met |
| STRESS-0005 | ENG-0008-103 | <!DOCTYPE html>
<html lang="en">
  <head>
    <met |
| STRESS-0006 | ENG-0012-584 | <!DOCTYPE html>
<html lang="en">
  <head>
    <met |
| STRESS-0007 | ENG0012584 | <!DOCTYPE html>
<html lang="en">
  <head>
    <met |
| STRESS-0008 | eng-0012-584 | <!DOCTYPE html>
<html lang="en">
  <head>
    <met |
| STRESS-0009 | eng0012584 | <!DOCTYPE html>
<html lang="en">
  <head>
    <met |
| STRESS-0010 | ENG-0012-584 | <!DOCTYPE html>
<html lang="en">
  <head>
    <met |

## Failure Signatures

- **<!DOCTYPE html>
<html lang="en...**: 17 occurrences (STRESS-0205, STRESS-1251, STRESS-1252, STRESS-1253, STRESS-1254...)
- **HTTPSConnectionPool(host='extr...**: 1 occurrences (STRESS-1250)
