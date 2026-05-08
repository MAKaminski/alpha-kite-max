import type { ReactNode } from "react";
import { classNames } from "@/lib/format";

export interface Column<T> {
  /** Header label. */
  header: string;
  /** Render the cell for a given row. */
  cell: (row: T) => ReactNode;
  /** Optional alignment. Defaults to left. */
  align?: "left" | "right" | "center";
  /** Optional className applied to <td>. */
  className?: string;
}

export interface TableProps<T> {
  columns: ReadonlyArray<Column<T>>;
  rows: ReadonlyArray<T>;
  /** Stable row key. */
  rowKey: (row: T, index: number) => string | number;
  /** Optional caption rendered above the table. */
  caption?: string;
}

export function Table<T>({ columns, rows, rowKey, caption }: TableProps<T>) {
  return (
    <div className="overflow-x-auto rounded-md border border-[var(--border)]">
      {caption ? (
        <div className="border-b border-[var(--border)] bg-[var(--row-alt)] px-4 py-2 text-xs uppercase tracking-wider text-[var(--muted)]">
          {caption}
        </div>
      ) : null}
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[var(--border)] bg-[var(--row-alt)]">
            {columns.map((c, i) => (
              <th
                key={i}
                className={classNames(
                  "px-3 py-2 text-xs font-medium uppercase tracking-wider text-[var(--muted)]",
                  c.align === "right"
                    ? "text-right"
                    : c.align === "center"
                      ? "text-center"
                      : "text-left",
                )}
              >
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, idx) => (
            <tr
              key={rowKey(row, idx)}
              className={classNames(
                "border-b border-[var(--border)] last:border-b-0",
                idx % 2 === 1 ? "bg-[var(--row-alt)]" : "",
              )}
            >
              {columns.map((c, i) => (
                <td
                  key={i}
                  className={classNames(
                    "px-3 py-2 align-top",
                    c.align === "right"
                      ? "text-right font-mono"
                      : c.align === "center"
                        ? "text-center"
                        : "text-left",
                    c.className,
                  )}
                >
                  {c.cell(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
