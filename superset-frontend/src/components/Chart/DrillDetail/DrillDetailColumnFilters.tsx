/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */
import { useState } from 'react';
import {
  BinaryQueryObjectFilterClause,
  css,
  GenericDataType,
  t,
  useTheme,
} from '@superset-ui/core';
import { Input } from 'src/components/Input';
import Button from 'src/components/Button';

type SearchFilter = Omit<BinaryQueryObjectFilterClause, 'formattedVal'>;

const COMPARISON = /^(>=|<=|>|<|=)?\s*(.+)$/;
const NUMBER = /^-?[\d\s]*[.,]?\d+$/;
const ISO_DATE = /^(\d{4})(?:-(\d{1,2})(?:-(\d{1,2}))?)?$/;
const FR_DATE = /^(?:(\d{1,2})\/)?(\d{1,2})\/(\d{4})$/;
const TRUE_VALUES = ['oui', 'vrai', 'true', '1'];
const FALSE_VALUES = ['non', 'faux', 'false', '0'];

// "2020", "2020-03", "2020-03-15", "03/2020" or "15/03/2020" give the
// [start, end) period in epoch ms, which the backend converts to a datetime.
const parsePeriod = (text: string): [number, number] | undefined => {
  let year: number;
  let month: number | undefined;
  let day: number | undefined;
  const iso = ISO_DATE.exec(text);
  const fr = FR_DATE.exec(text);
  if (iso) {
    year = Number(iso[1]);
    month = iso[2] ? Number(iso[2]) : undefined;
    day = iso[3] ? Number(iso[3]) : undefined;
  } else if (fr) {
    year = Number(fr[3]);
    month = Number(fr[2]);
    day = fr[1] ? Number(fr[1]) : undefined;
  } else {
    return undefined;
  }
  if (month === undefined) {
    return [Date.UTC(year, 0, 1), Date.UTC(year + 1, 0, 1)];
  }
  if (day === undefined) {
    return [Date.UTC(year, month - 1, 1), Date.UTC(year, month, 1)];
  }
  return [Date.UTC(year, month - 1, day), Date.UTC(year, month - 1, day + 1)];
};

const buildColumnFilters = (
  col: string,
  text: string,
  type?: GenericDataType,
): SearchFilter[] | undefined => {
  const [, op = '', raw] = COMPARISON.exec(text) ?? [];
  if (!raw) return undefined;
  if (type === GenericDataType.Numeric) {
    if (!NUMBER.test(raw)) return undefined;
    const val = Number(raw.replace(/\s/g, '').replace(',', '.'));
    return [{ col, op: !op || op === '=' ? '==' : op, val } as SearchFilter];
  }
  if (type === GenericDataType.Temporal) {
    const period = parsePeriod(raw);
    if (!period) return undefined;
    const [start, end] = period;
    if (op === '>') return [{ col, op: '>=', val: end }];
    if (op === '>=') return [{ col, op: '>=', val: start }];
    if (op === '<') return [{ col, op: '<', val: start }];
    if (op === '<=') return [{ col, op: '<', val: end }];
    return [
      { col, op: '>=', val: start },
      { col, op: '<', val: end },
    ];
  }
  if (type === GenericDataType.Boolean) {
    const lower = raw.toLowerCase();
    if (TRUE_VALUES.includes(lower)) return [{ col, op: '==', val: true }];
    if (FALSE_VALUES.includes(lower)) return [{ col, op: '==', val: false }];
    return undefined;
  }
  return [{ col, op: 'ILIKE', val: `%${text}%` }];
};

// Text columns: "contains" (case insensitive); numbers: "100", ">100", "<=5";
// dates: "2020", "03/2020", ">=01/01/2020"; booleans: "oui" / "non".
export const buildSearchFilters = (
  values: Record<string, string>,
  colNames: string[],
  colTypes: GenericDataType[],
) =>
  Object.entries(values).reduce<{
    filters: SearchFilter[];
    invalid: string[];
  }>(
    (acc, [name, value]) => {
      const text = value.trim();
      if (!text) return acc;
      const filters = buildColumnFilters(
        name,
        text,
        colTypes[colNames.indexOf(name)],
      );
      if (filters) acc.filters.push(...filters);
      else acc.invalid.push(name);
      return acc;
    },
    { filters: [], invalid: [] },
  );

const placeholderFor = (type?: GenericDataType) => {
  if (type === GenericDataType.Numeric) return t('ex. >100');
  if (type === GenericDataType.Temporal) return t('ex. 2020, >=01/03/2021');
  if (type === GenericDataType.Boolean) return t('oui / non');
  return t('Contient…');
};

export default function DrillDetailColumnFilters({
  colNames,
  colTypes,
  values,
  invalid,
  onChange,
}: {
  colNames: string[];
  colTypes: GenericDataType[];
  values: Record<string, string>;
  invalid: string[];
  onChange: (values: Record<string, string>) => void;
}) {
  const theme = useTheme();
  const [shown, setShown] = useState(false);
  const activeCount = Object.values(values).filter(value =>
    value.trim(),
  ).length;

  return (
    <div
      css={css`
        margin-bottom: ${theme.gridUnit * 2}px;
      `}
      data-test="drill-detail-column-filters"
    >
      <Button
        buttonStyle="link"
        buttonSize="small"
        onClick={() => setShown(value => !value)}
      >
        {activeCount
          ? t('Filtrer par colonne (%s)', activeCount)
          : t('Filtrer par colonne')}
      </Button>
      {activeCount > 0 && (
        <Button
          buttonStyle="link"
          buttonSize="small"
          onClick={() => onChange({})}
        >
          {t('Effacer')}
        </Button>
      )}
      {shown && (
        <div
          css={css`
            display: flex;
            flex-wrap: wrap;
            gap: ${theme.gridUnit * 2}px;
            margin-top: ${theme.gridUnit}px;
            max-height: ${theme.gridUnit * 40}px;
            overflow-y: auto;
          `}
        >
          {colNames.map((name, index) => (
            <div
              key={name}
              css={css`
                display: flex;
                flex-direction: column;
                width: ${theme.gridUnit * 40}px;
                font-size: ${theme.typography.sizes.s}px;
                color: ${theme.colors.grayscale.base};
              `}
            >
              {name}
              <Input
                size="small"
                allowClear
                aria-label={name}
                title={
                  invalid.includes(name) ? t('Valeur non reconnue') : undefined
                }
                css={
                  invalid.includes(name) &&
                  css`
                    &&& {
                      border-color: ${theme.colors.error.base};
                    }
                  `
                }
                value={values[name] ?? ''}
                placeholder={placeholderFor(colTypes[index])}
                onChange={e => onChange({ ...values, [name]: e.target.value })}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
