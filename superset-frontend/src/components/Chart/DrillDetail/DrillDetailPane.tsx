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
import {
  cloneElement,
  ReactElement,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { useSelector } from 'react-redux';
import {
  BinaryQueryObjectFilterClause,
  css,
  ensureIsArray,
  GenericDataType,
  getTimeFormatter,
  JsonObject,
  QueryFormData,
  t,
  TimeFormats,
  useTheme,
} from '@superset-ui/core';
import { isEqual } from 'lodash';
import { useResizeDetector } from 'react-resize-detector';
import Loading from 'src/components/Loading';
import BooleanCell from 'src/components/Table/cell-renderers/BooleanCell';
import NullCell from 'src/components/Table/cell-renderers/NullCell';
import TimeCell from 'src/components/Table/cell-renderers/TimeCell';
import { EmptyStateMedium } from 'src/components/EmptyState';
import { getDatasourceSamples } from 'src/components/Chart/chartAction';
import Table, { ColumnsType, TableSize } from 'src/components/Table';
import HeaderWithRadioGroup from 'src/components/Table/header-renderers/HeaderWithRadioGroup';
import { ResourceStatus } from 'src/hooks/apiResources/apiResources';
import { useDatasetMetadataBar } from 'src/features/datasets/metadataBar/useDatasetMetadataBar';
import { Input } from 'src/components/Input';
import { compareCellValues } from 'src/explore/components/DataTableControl';
import TableControls from './DrillDetailTableControls';
import DrillDetailColumnFilters, {
  buildSearchFilters,
} from './DrillDetailColumnFilters';
import { getDrillPayload } from './utils';
import { ResultsPage } from './types';

const PAGE_SIZE = 50;
const SEARCH_DEBOUNCE = 500;
const MAX_CLIENT_CHUNKS = 10;
const timeFormatter = getTimeFormatter(TimeFormats.DATABASE_DATETIME);

const normalize = (value: unknown) =>
  String(value)
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase();

interface DataType {
  [key: string]: any;
}

// Must be outside of the main component due to problems in
// react-resize-detector with conditional rendering
// https://github.com/maslianok/react-resize-detector/issues/178
function Resizable({ children }: { children: ReactElement }) {
  const { ref, height } = useResizeDetector();
  return (
    <div ref={ref} css={{ flex: 1 }}>
      {cloneElement(children, { height })}
    </div>
  );
}

enum TimeFormatting {
  Original,
  Formatted,
}

export default function DrillDetailPane({
  formData,
  initialFilters,
}: {
  formData: QueryFormData;
  initialFilters: BinaryQueryObjectFilterClause[];
}) {
  const theme = useTheme();
  const [pageIndex, setPageIndex] = useState(0);
  const lastPageIndex = useRef(pageIndex);
  const [filters, setFilters] = useState(initialFilters);
  const [isLoading, setIsLoading] = useState(false);
  const [responseError, setResponseError] = useState('');
  const [resultsPages, setResultsPages] = useState<Map<number, ResultsPage>>(
    new Map(),
  );
  const [timeFormatting, setTimeFormatting] = useState({});
  const [columnSearch, setColumnSearch] = useState<Record<string, string>>({});
  const [searchFilters, setSearchFilters] = useState<
    BinaryQueryObjectFilterClause[]
  >([]);
  const [quickSearch, setQuickSearch] = useState('');
  const [isSorted, setIsSorted] = useState(false);
  const [knownColumns, setKnownColumns] = useState<{
    names: string[];
    types: GenericDataType[];
  }>({ names: [], types: [] });

  const SAMPLES_ROW_LIMIT = useSelector(
    (state: { common: { conf: JsonObject } }) =>
      state.common.conf.SAMPLES_ROW_LIMIT ?? 1000,
  );
  const maxClientRows = SAMPLES_ROW_LIMIT * MAX_CLIENT_CHUNKS;

  // Extract datasource ID/type from string ID
  const [datasourceId, datasourceType] = useMemo(
    () => formData.datasource.split('__'),
    [formData.datasource],
  );

  const { metadataBar, status: metadataBarStatus } = useDatasetMetadataBar({
    datasetId: datasourceId,
  });
  // Get page of results
  const resultsPage = useMemo(() => {
    const nextResultsPage = resultsPages.get(pageIndex);
    if (nextResultsPage) {
      lastPageIndex.current = pageIndex;
      return nextResultsPage;
    }

    return resultsPages.get(lastPageIndex.current);
  }, [pageIndex, resultsPages]);

  // Up to maxClientRows rows are all loaded, so sorting, searching and paging
  // are done in the browser on the whole result; beyond that, pages come
  // from the server and only the displayed page can be sorted or searched.
  const total = resultsPages.get(0)?.total ?? resultsPage?.total;
  const isClientSide = total !== undefined && total <= maxClientRows;

  useEffect(() => {
    if (resultsPage?.colNames.length) {
      setKnownColumns(prev =>
        isEqual(prev.names, resultsPage.colNames)
          ? prev
          : { names: resultsPage.colNames, types: resultsPage.colTypes },
      );
    }
  }, [resultsPage]);

  const invalidSearchColumns = useMemo(
    () =>
      buildSearchFilters(columnSearch, knownColumns.names, knownColumns.types)
        .invalid,
    [columnSearch, knownColumns],
  );

  useEffect(() => {
    const timer = setTimeout(() => {
      const next = buildSearchFilters(
        columnSearch,
        knownColumns.names,
        knownColumns.types,
      ).filters as BinaryQueryObjectFilterClause[];
      setSearchFilters(prev => (isEqual(prev, next) ? prev : next));
    }, SEARCH_DEBOUNCE);
    return () => clearTimeout(timer);
  }, [columnSearch, knownColumns]);

  const mappedColumns: ColumnsType<DataType> = useMemo(
    () =>
      resultsPage?.colNames.map((column, index) => ({
        key: column,
        dataIndex: column,
        title:
          resultsPage?.colTypes[index] === GenericDataType.Temporal ? (
            <HeaderWithRadioGroup
              headerTitle={column}
              groupTitle={t('Formatting')}
              groupOptions={[
                { label: t('Original value'), value: TimeFormatting.Original },
                {
                  label: t('Formatted value'),
                  value: TimeFormatting.Formatted,
                },
              ]}
              value={
                timeFormatting[column] === TimeFormatting.Original
                  ? TimeFormatting.Original
                  : TimeFormatting.Formatted
              }
              onChange={value =>
                setTimeFormatting(state => ({ ...state, [column]: value }))
              }
            />
          ) : (
            column
          ),
        render: value => {
          if (value === true || value === false) {
            return <BooleanCell value={value} />;
          }
          if (value === null) {
            return <NullCell />;
          }
          if (
            resultsPage?.colTypes[index] === GenericDataType.Temporal &&
            timeFormatting[column] !== TimeFormatting.Original &&
            (typeof value === 'number' || value instanceof Date)
          ) {
            return <TimeCell value={value} />;
          }
          return String(value);
        },
        sorter: (a: DataType, b: DataType, sortOrder?: string | null) =>
          compareCellValues(a[column], b[column], sortOrder === 'descend'),
        width: 150,
      })) || [],
    [resultsPage?.colNames, resultsPage?.colTypes, timeFormatting],
  );

  const rows = useMemo(() => {
    if (!isClientSide || total === undefined) return resultsPage?.data || [];
    const pageCount = Math.ceil(total / PAGE_SIZE);
    return Array.from(
      { length: pageCount },
      (_, index) => resultsPages.get(index)?.data || [],
    ).flat();
  }, [isClientSide, total, resultsPage?.data, resultsPages]);

  const data: DataType[] = useMemo(
    () =>
      rows.map(
        (row, index) =>
          resultsPage?.colNames.reduce(
            (acc, curr) => ({ ...acc, [curr]: row[curr] }),
            {
              key: index,
            },
          ) || { key: index },
      ),
    [resultsPage?.colNames, rows],
  );

  const displayedData = useMemo(() => {
    const needle = normalize(quickSearch.trim());
    if (!needle) return data;
    const colNames = resultsPage?.colNames || [];
    const colTypes = resultsPage?.colTypes || [];
    return data.filter(row =>
      colNames.some((name, index) => {
        const value = row[name];
        if (value === null || value === undefined) return false;
        const text =
          colTypes[index] === GenericDataType.Temporal &&
          typeof value === 'number'
            ? timeFormatter(value)
            : value;
        return normalize(text).includes(needle);
      }),
    );
  }, [data, quickSearch, resultsPage?.colNames, resultsPage?.colTypes]);

  // Clear cache on reload button click
  const handleReload = useCallback(() => {
    setResponseError('');
    setResultsPages(new Map());
    setPageIndex(0);
    setIsSorted(false);
  }, []);

  // Clear cache and reset page index if filters change
  useEffect(() => {
    setResponseError('');
    setResultsPages(new Map());
    setPageIndex(0);
    setIsSorted(false);
  }, [filters, searchFilters]);

  // Update cache order if page in cache
  useEffect(() => {
    if (
      resultsPages.has(pageIndex) &&
      [...resultsPages.keys()].at(-1) !== pageIndex
    ) {
      const nextResultsPages = new Map(resultsPages);
      nextResultsPages.delete(pageIndex);
      setResultsPages(
        nextResultsPages.set(
          pageIndex,
          resultsPages.get(pageIndex) as ResultsPage,
        ),
      );
    }
  }, [pageIndex, resultsPages]);

  // Download page of results & trim cache if page not in cache
  useEffect(() => {
    if (!responseError && !isLoading && !resultsPages.has(pageIndex)) {
      setIsLoading(true);
      const jsonPayload =
        getDrillPayload(formData, [...filters, ...searchFilters]) ?? {};
      const cachePageLimit = Math.ceil(SAMPLES_ROW_LIMIT / PAGE_SIZE);
      // the first load fetches every row (in SAMPLES_ROW_LIMIT chunks, the
      // largest page the API accepts) as long as there are at most
      // maxClientRows of them, then splits them into pages
      const isFirstLoad = resultsPages.size === 0 && pageIndex === 0;
      const fetchSamples = (perPage: number, page: number) =>
        getDatasourceSamples(
          datasourceType,
          datasourceId,
          false,
          jsonPayload,
          perPage,
          page,
        );
      const request = isFirstLoad
        ? fetchSamples(SAMPLES_ROW_LIMIT, 1).then(async first => {
            const chunkCount = Math.ceil(first.total_count / SAMPLES_ROW_LIMIT);
            if (chunkCount <= 1 || first.total_count > maxClientRows) {
              return first;
            }
            const rest = await Promise.all(
              Array.from({ length: chunkCount - 1 }, (_, index) =>
                fetchSamples(SAMPLES_ROW_LIMIT, index + 2),
              ),
            );
            return {
              ...first,
              data: [first, ...rest].flatMap(chunk => chunk.data),
            };
          })
        : fetchSamples(PAGE_SIZE, pageIndex + 1);
      request
        .then(response => {
          const page = (data: Record<string, any>[]) => ({
            total: response.total_count,
            data,
            colNames: ensureIsArray(response.colnames),
            colTypes: ensureIsArray(response.coltypes),
          });
          if (isFirstLoad) {
            const chunks = Math.max(
              Math.ceil(response.data.length / PAGE_SIZE),
              1,
            );
            setResultsPages(
              new Map(
                Array.from({ length: chunks }, (_, index) => [
                  index,
                  page(
                    response.data.slice(
                      index * PAGE_SIZE,
                      (index + 1) * PAGE_SIZE,
                    ),
                  ),
                ]),
              ),
            );
          } else {
            setResultsPages(
              new Map([
                ...[...resultsPages.entries()].slice(-cachePageLimit + 1),
                [pageIndex, page(response.data)],
              ]),
            );
          }
          setResponseError('');
        })
        .catch(error => {
          setResponseError(`${error.name}: ${error.message}`);
        })
        .finally(() => {
          setIsLoading(false);
        });
    }
  }, [
    SAMPLES_ROW_LIMIT,
    maxClientRows,
    datasourceId,
    datasourceType,
    filters,
    formData,
    isLoading,
    pageIndex,
    responseError,
    resultsPages,
    searchFilters,
  ]);

  const bootstrapping =
    (!responseError && !resultsPages.size) ||
    metadataBarStatus === ResourceStatus.Loading;

  const allowHTML = formData.allow_render_html ?? true;

  let tableContent = null;
  if (responseError) {
    // Render error if page download failed
    tableContent = (
      <pre
        css={css`
          margin-top: ${theme.gridUnit * 4}px;
        `}
      >
        {responseError}
      </pre>
    );
  } else if (bootstrapping) {
    // Render loading if first page hasn't loaded
    tableContent = <Loading />;
  } else if (resultsPage?.total === 0) {
    // Render empty state if no results are returned for page
    const title = t('No rows were returned for this dataset');
    tableContent = <EmptyStateMedium image="document.svg" title={title} />;
  } else {
    // Render table if at least one page has successfully loaded
    tableContent = (
      <Resizable>
        <Table
          data={displayedData}
          columns={mappedColumns}
          size={TableSize.Small}
          defaultPageSize={PAGE_SIZE}
          recordCount={isClientSide ? displayedData.length : resultsPage?.total}
          usePagination
          loading={isLoading}
          onChange={(pagination, _filters, sorter, extra) => {
            if (extra?.action === 'sort') {
              setIsSorted(
                ensureIsArray(sorter).some(
                  item => item && 'order' in item && !!item.order,
                ),
              );
            }
            if (!isClientSide) {
              setPageIndex(pagination.current ? pagination.current - 1 : 0);
            }
          }}
          resizable
          virtualize
          allowHTML={allowHTML}
        />
      </Resizable>
    );
  }

  const showControls =
    !bootstrapping ||
    (knownColumns.names.length > 0 &&
      metadataBarStatus !== ResourceStatus.Loading);

  return (
    <>
      {showControls && metadataBar}
      {showControls && (
        <TableControls
          filters={filters}
          setFilters={setFilters}
          totalCount={
            quickSearch.trim() && isClientSide
              ? displayedData.length
              : resultsPage?.total
          }
          loading={isLoading}
          onReload={handleReload}
        />
      )}
      {showControls && (
        <div
          css={css`
            display: flex;
            align-items: flex-start;
            gap: ${theme.gridUnit * 2}px;
          `}
        >
          <div
            css={css`
              flex: 1;
              min-width: 0;
            `}
          >
            <DrillDetailColumnFilters
              colNames={knownColumns.names}
              colTypes={knownColumns.types}
              values={columnSearch}
              invalid={invalidSearchColumns}
              onChange={setColumnSearch}
            />
          </div>
          <Input
            size="small"
            allowClear
            aria-label={t('Rechercher dans le tableau')}
            placeholder={t('Rechercher dans le tableau')}
            value={quickSearch}
            onChange={e => setQuickSearch(e.target.value)}
            css={css`
              width: ${theme.gridUnit * 60}px;
            `}
          />
        </div>
      )}
      {showControls && !isClientSide && (isSorted || quickSearch.trim()) && (
        <div
          css={css`
            margin-bottom: ${theme.gridUnit * 2}px;
            font-size: ${theme.typography.sizes.s}px;
            color: ${theme.colors.grayscale.base};
          `}
        >
          {t(
            'Plus de %s lignes : le tri et la recherche ne portent que sur la page affichée. Utilisez « Filtrer par colonne » pour cibler toutes les lignes.',
            maxClientRows,
          )}
        </div>
      )}
      {tableContent}
    </>
  );
}
