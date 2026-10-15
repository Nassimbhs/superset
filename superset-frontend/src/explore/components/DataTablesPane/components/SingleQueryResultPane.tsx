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
import { useMemo, useState } from 'react';
import {
  css,
  GenericDataType,
  getTimeFormatter,
  t,
  TimeFormats,
  useTheme,
} from '@superset-ui/core';
import TableView, { EmptyWrapperType } from 'src/components/TableView';
import { Input } from 'src/components/Input';
import Button from 'src/components/Button';
import {
  useFilteredTableData,
  useTableColumns,
} from 'src/explore/components/DataTableControl';
import { TableControls } from './DataTableControls';
import { SingleQueryResultPaneProp } from '../types';

const timeFormatter = getTimeFormatter(TimeFormats.DATABASE_DATETIME);
const NUMBER_FILTER = /^(>=|<=|>|<|=)\s*(-?[\d\s]*[.,]?\d+)$/;

const normalize = (value: unknown) =>
  String(value)
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase();

// "texte" keeps rows containing it (case and accent insensitive);
// ">100", "<=5", "=12" compare numerically on number columns.
const buildCellMatcher = (filter: string, type?: GenericDataType) => {
  const numeric = NUMBER_FILTER.exec(filter.trim());
  if (numeric && type === GenericDataType.Numeric) {
    const [, op, raw] = numeric;
    const target = Number(raw.replace(/\s/g, '').replace(',', '.'));
    return (value: unknown) => {
      if (typeof value !== 'number') return false;
      if (op === '>') return value > target;
      if (op === '<') return value < target;
      if (op === '>=') return value >= target;
      if (op === '<=') return value <= target;
      return value === target;
    };
  }
  const needle = normalize(filter.trim());
  return (value: unknown) => {
    if (value === null || value === undefined) return false;
    const text =
      type === GenericDataType.Temporal && typeof value === 'number'
        ? timeFormatter(value)
        : value;
    return normalize(text).includes(needle);
  };
};

export const SingleQueryResultPane = ({
  data,
  colnames,
  coltypes,
  rowcount,
  datasourceId,
  dataSize = 50,
  isVisible,
  canDownload,
  showColumnFilters = false,
}: SingleQueryResultPaneProp) => {
  const theme = useTheme();
  const [filterText, setFilterText] = useState('');
  const [columnFilters, setColumnFilters] = useState<Record<string, string>>(
    {},
  );
  const [showFilters, setShowFilters] = useState(false);

  // this is to preserve the order of the columns, even if there are integer values,
  // while also only grabbing the first column's keys
  const columns = useTableColumns(
    colnames,
    coltypes,
    data,
    datasourceId,
    isVisible,
    {}, // moreConfig
    true, // allowHTML
  );
  const searchedData = useFilteredTableData(filterText, data);

  const activeFilters = useMemo(
    () =>
      Object.entries(columnFilters)
        .filter(([, value]) => value.trim())
        .map(([name, value]) => ({
          name,
          matches: buildCellMatcher(value, coltypes?.[colnames.indexOf(name)]),
        })),
    [colnames, coltypes, columnFilters],
  );

  const filteredData = useMemo(
    () =>
      activeFilters.length
        ? searchedData.filter(row =>
            activeFilters.every(({ name, matches }) => matches(row[name])),
          )
        : searchedData,
    [activeFilters, searchedData],
  );

  return (
    <>
      <TableControls
        data={filteredData}
        columnNames={colnames}
        columnTypes={coltypes}
        rowcount={rowcount}
        datasourceId={datasourceId}
        onInputChange={input => setFilterText(input)}
        isLoading={false}
        canDownload={canDownload}
      />
      {showColumnFilters && (
        <div
          css={css`
            margin-bottom: ${theme.gridUnit * 2}px;
          `}
          data-test="column-filters"
        >
          <Button
            buttonStyle="link"
            buttonSize="small"
            onClick={() => setShowFilters(shown => !shown)}
          >
            {activeFilters.length
              ? t('Filtrer par colonne (%s)', activeFilters.length)
              : t('Filtrer par colonne')}
          </Button>
          {activeFilters.length > 0 && (
            <Button
              buttonStyle="link"
              buttonSize="small"
              onClick={() => setColumnFilters({})}
            >
              {t('Effacer')}
            </Button>
          )}
          {showFilters && (
            <div
              css={css`
                display: flex;
                flex-wrap: wrap;
                gap: ${theme.gridUnit * 2}px;
                margin-top: ${theme.gridUnit}px;
              `}
            >
              {colnames.map((name, index) => (
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
                    value={columnFilters[name] ?? ''}
                    placeholder={
                      coltypes?.[index] === GenericDataType.Numeric
                        ? t('ex. >100')
                        : t('Contient…')
                    }
                    onChange={e => {
                      const { value } = e.target;
                      setColumnFilters(prev => ({ ...prev, [name]: value }));
                    }}
                  />
                </div>
              ))}
            </div>
          )}
        </div>
      )}
      <TableView
        columns={columns}
        data={filteredData}
        pageSize={dataSize}
        noDataText={t('No results')}
        emptyWrapperType={EmptyWrapperType.Small}
        className="table-condensed"
        isPaginationSticky
        showRowCount={false}
        small
      />
    </>
  );
};
