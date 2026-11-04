"use client";

interface PaginationProps {
	page: number;
	pageSize: number;
	total: number;
	onPageChange: (page: number) => void;
	idPrefix?: string;
	showSummary?: boolean;
}

export default function Pagination({
	page,
	pageSize,
	total,
	onPageChange,
	idPrefix = "pagination",
	showSummary = false,
}: PaginationProps) {
	const totalPages = Math.ceil(total / pageSize);
	if (totalPages <= 1 && !showSummary) return null;

	const visiblePages = Array.from({ length: totalPages }, (_, index) => index + 1).filter(
		(visiblePage) => visiblePage === 1 || visiblePage === totalPages || Math.abs(visiblePage - page) <= 2,
	);
	const pageItems: Array<number | "…"> = [];
	for (const [index, visiblePage] of visiblePages.entries()) {
		const previousPage = visiblePages[index - 1];
		if (previousPage !== undefined && visiblePage - previousPage > 1) pageItems.push("…");
		pageItems.push(visiblePage);
	}

	return (
		<div
			style={{
				display: "flex",
				alignItems: "center",
				justifyContent: showSummary ? "space-between" : "center",
				gap: 6,
				marginTop: showSummary ? 14 : 36,
				paddingBottom: 8,
				flexWrap: "wrap",
			}}>
			{showSummary && (
				<span
					aria-live='polite'
					style={{
						fontSize: 12,
						color: "var(--text-muted)",
						whiteSpace: "nowrap",
					}}>
					Showing {total === 0 ? 0 : (page - 1) * pageSize + 1}–{Math.min(page * pageSize, total)} of{" "}
					{total.toLocaleString()}
				</span>
			)}
			{totalPages > 1 && (
				<div
					role='navigation'
					aria-label={`${idPrefix} pages`}
					style={{ display: "flex", alignItems: "center", gap: 6 }}>
					<button
						type='button'
						id={`${idPrefix}-prev`}
						className='btn btn-ghost btn-sm'
						disabled={page <= 1}
						onClick={() => onPageChange(page - 1)}
						style={{ gap: 4 }}>
						<svg width='14' height='14' viewBox='0 0 14 14' fill='none'>
							<path
								d='M9 11L5 7l4-4'
								stroke='currentColor'
								strokeWidth='1.5'
								strokeLinecap='round'
								strokeLinejoin='round'
							/>
						</svg>
						Prev
					</button>

					{pageItems.map((item, index) =>
						item === "…" ?
							<span key={`ellipsis-${index}`} style={{ color: "var(--text-muted)", fontSize: 13, padding: "0 4px" }}>
								&hellip;
							</span>
						:	<button
								type='button'
								key={item}
								id={`${idPrefix}-page-${item}`}
								className={item === page ? "btn btn-primary btn-sm" : "btn btn-ghost btn-sm"}
								style={{ minWidth: 36 }}
								aria-current={item === page ? "page" : undefined}
								onClick={() => onPageChange(item)}>
								{item}
							</button>,
					)}

					<button
						type='button'
						id={`${idPrefix}-next`}
						className='btn btn-ghost btn-sm'
						disabled={page >= totalPages}
						onClick={() => onPageChange(page + 1)}
						style={{ gap: 4 }}>
						Next
						<svg width='14' height='14' viewBox='0 0 14 14' fill='none'>
							<path
								d='M5 3l4 4-4 4'
								stroke='currentColor'
								strokeWidth='1.5'
								strokeLinecap='round'
								strokeLinejoin='round'
							/>
						</svg>
					</button>
				</div>
			)}
		</div>
	);
}
