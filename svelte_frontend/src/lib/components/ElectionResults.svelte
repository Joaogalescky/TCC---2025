<script lang="ts" module>
	export interface CandidateResult {
		id: number;
		username: string;
		votes: number;
	}

	export interface ElectionResultsData {
		election_id: number;
		candidates: CandidateResult[];
		total_votes: number;
	}
</script>

<script lang="ts">
	interface Props {
		results: ElectionResultsData;
	}

	let { results }: Props = $props();

	let ranking = $derived(
		[...results.candidates].sort((a, b) => b.votes - a.votes),
	);
	let topVotes = $derived(ranking[0]?.votes ?? 0);

	function percent(votes: number) {
		return results.total_votes > 0
			? Math.round((votes / results.total_votes) * 1000) / 10
			: 0;
	}
</script>

<div class="space-y-3">
	{#if ranking.length === 0}
		<p class="text-sm text-gray-500">Nenhum candidato nesta eleição</p>
	{:else}
		<ol class="space-y-3">
			{#each ranking as candidate}
				<li>
					<div class="flex justify-between items-baseline text-sm mb-1">
						<span class="font-medium text-gray-900">
							{candidate.username}
							{#if topVotes > 0 && candidate.votes === topVotes}
								<span
									class="ml-1 text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full"
									>Mais votado</span
								>
							{/if}
						</span>
						<span class="text-gray-600 tabular-nums">
							{candidate.votes}
							{candidate.votes === 1 ? "voto" : "votos"} · {percent(
								candidate.votes,
							)}%
						</span>
					</div>
					<div class="h-2 bg-gray-100 rounded-full overflow-hidden">
						<div
							class="h-full bg-blue-600 rounded-full"
							style="width: {percent(candidate.votes)}%"
						></div>
					</div>
				</li>
			{/each}
		</ol>
	{/if}
	<p class="text-sm text-gray-600">
		Total de votos: <span class="font-medium tabular-nums"
			>{results.total_votes}</span
		>
	</p>
</div>
