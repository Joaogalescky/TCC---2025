<script lang="ts">
	import { browser } from "$app/environment";
	import { goto } from "$app/navigation";
	import { onMount } from "svelte";
	import { api, ApiError } from "../../lib/api";
	import { auth, authActions, type User } from "../../lib/stores/auth";
	import Toast from "$lib/components/Toast.svelte";
	import ElectionStatusBadge from "$lib/components/ElectionStatusBadge.svelte";
	import ElectionResults, {
		type ElectionResultsData,
	} from "$lib/components/ElectionResults.svelte";

	interface Candidate {
		id: number;
		username: string;
		is_deleted?: boolean;
	}

	interface ElectionWithCandidates {
		id: number;
		title: string;
		status: string;
		has_votes: boolean;
		candidates: Candidate[];
	}

	let users: User[] = [];
	let candidates: Candidate[] = [];
	let elections: ElectionWithCandidates[] = [];
	// Resultados das eleições já apuradas, por id da eleição
	let results: Record<number, ElectionResultsData> = {};
	let newElectionTitle = "";
	// Candidato escolhido no seletor de cada eleição
	let selectedCandidate: Record<number, number | ""> = {};
	let loading = false;
	let message = "";
	let messageType: "success" | "error" = "success";

	$: if (browser && !$auth.isAuthenticated) {
		goto("/login");
	} else if (browser && !$auth.user?.is_admin) {
		goto("/election");
	}

	onMount(loadAll);

	async function loadAll() {
		loading = true;
		try {
			const [usersResponse, candidatesResponse, electionsResponse] =
				await Promise.all([
					api.getUsers(),
					api.getCandidates(),
					api.getElections(),
				]);
			users = usersResponse.users;
			candidates = candidatesResponse.candidates;
			elections = await Promise.all(
				electionsResponse.elections.map((e: { id: number }) =>
					api.getElectionCandidates(e.id),
				),
			);
			const tallied = elections.filter((e) => e.status === "tallied");
			const talliedResults = await Promise.all(
				tallied.map((e) => api.getResults(e.id)),
			);
			results = Object.fromEntries(
				talliedResults.map((r: ElectionResultsData) => [r.election_id, r]),
			);
		} catch (e) {
			showError(e, "Erro ao carregar dados");
		} finally {
			loading = false;
		}
	}

	async function toggleCandidate(user: User) {
		try {
			await api.setCandidate(user.id, !user.is_candidate);
			showMessage(
				user.is_candidate
					? `${user.username} agora é eleitor`
					: `${user.username} agora é candidato`,
				"success",
			);
			await loadAll();
		} catch (e) {
			showError(e, "Erro ao alterar o papel do usuário");
		}
	}

	async function createElection() {
		if (!newElectionTitle.trim()) return;
		try {
			await api.createElection(newElectionTitle.trim());
			newElectionTitle = "";
			showMessage("Eleição criada", "success");
			await loadAll();
		} catch (e) {
			showError(e, "Erro ao criar eleição");
		}
	}

	async function deleteElection(election: ElectionWithCandidates) {
		try {
			await api.deleteElection(election.id);
			showMessage("Eleição excluída", "success");
			await loadAll();
		} catch (e) {
			showError(e, "Erro ao excluir eleição");
		}
	}

	async function openElection(election: ElectionWithCandidates) {
		if (
			!confirm(
				`Abrir a votação de "${election.title}"? Depois disso a lista de candidatos não poderá ser alterada.`,
			)
		)
			return;
		try {
			await api.openElection(election.id);
			showMessage("Votação aberta", "success");
			await loadAll();
		} catch (e) {
			showError(e, "Erro ao abrir a votação");
		}
	}

	async function closeElection(election: ElectionWithCandidates) {
		if (
			!confirm(
				`Encerrar "${election.title}"? Nenhum voto novo será aceito.`,
			)
		)
			return;
		try {
			await api.closeElection(election.id);
			showMessage("Eleição encerrada", "success");
			await loadAll();
		} catch (e) {
			showError(e, "Erro ao encerrar eleição");
		}
	}

	async function tallyElection(election: ElectionWithCandidates) {
		try {
			await api.tallyElection(election.id);
			showMessage("Votos apurados e resultado publicado", "success");
			await loadAll();
		} catch (e) {
			showError(e, "Erro ao apurar votos");
		}
	}

	async function cancelElection(election: ElectionWithCandidates) {
		if (
			!confirm(
				`Cancelar "${election.title}"? A eleição não será apurada; votos e candidatos ficam guardados como histórico.`,
			)
		)
			return;
		try {
			await api.cancelElection(election.id);
			showMessage("Eleição cancelada", "success");
			await loadAll();
		} catch (e) {
			showError(e, "Erro ao cancelar eleição");
		}
	}

	async function deleteUser(user: User) {
		if (!confirm(`Excluir a conta de ${user.username}?`)) return;
		try {
			const response = await api.deleteUser(user.id);
			showMessage(
				response.message === "User deactivated"
					? `${user.username} participou de eleições: conta desativada e mantida no histórico`
					: `Conta de ${user.username} excluída`,
				"success",
			);
			await loadAll();
		} catch (e) {
			showError(e, "Erro ao excluir usuário");
		}
	}

	async function reactivateUser(user: User) {
		try {
			await api.reactivateUser(user.id);
			showMessage(`Conta de ${user.username} reativada`, "success");
			await loadAll();
		} catch (e) {
			showError(e, "Erro ao reativar usuário");
		}
	}

	async function addCandidate(election: ElectionWithCandidates) {
		const candidateId = selectedCandidate[election.id];
		if (!candidateId) return;
		try {
			await api.addCandidateToElection(election.id, candidateId);
			selectedCandidate[election.id] = "";
			await loadAll();
		} catch (e) {
			showError(e, "Erro ao vincular candidato");
		}
	}

	async function removeCandidate(
		election: ElectionWithCandidates,
		candidate: Candidate,
	) {
		try {
			await api.removeCandidateFromElection(election.id, candidate.id);
			await loadAll();
		} catch (e) {
			showError(e, "Erro ao desvincular candidato");
		}
	}

	function availableCandidates(election: ElectionWithCandidates) {
		const linked = new Set(election.candidates.map((c) => c.id));
		return candidates.filter((c) => !linked.has(c.id));
	}

	function showError(e: unknown, fallback: string) {
		showMessage(e instanceof ApiError ? e.message : fallback, "error");
	}

	function showMessage(text: string, type: "success" | "error") {
		message = text;
		messageType = type;
		setTimeout(() => (message = ""), 5000);
	}

	function logout() {
		authActions.logout();
		goto("/login");
	}
</script>

<div class="min-h-screen bg-gray-50">
	<nav class="bg-white shadow sticky top-0 z-50">
		<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
			<div class="flex justify-between h-16">
				<div class="flex items-center">
					<h1 class="text-xl font-semibold">Administração</h1>
				</div>
				<div class="flex items-center space-x-4">
					<a
						href="/election"
						class="text-blue-600 hover:text-blue-500 font-bold"
					>
						Eleições
					</a>
					<span class="text-gray-700"
						>Olá, {$auth.user?.username}</span
					>
					<button
						on:click={logout}
						class="text-gray-500 hover:text-gray-700 font-bold"
					>
						Sair
					</button>
				</div>
			</div>
		</div>
	</nav>

	<Toast {message} type={messageType} />

	<main class="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8 space-y-10">
		<section>
			<h2 class="text-2xl font-bold text-gray-900 mb-2">Usuários</h2>
			<p class="text-gray-600 mb-4">
				Todo usuário é eleitor. Marque como candidato quem poderá
				concorrer nas eleições. Candidatos também votam.
			</p>

			{#if loading && users.length === 0}
				<div class="text-gray-500">Carregando usuários...</div>
			{:else}
				<div class="bg-white shadow rounded-lg overflow-x-auto">
					<table class="min-w-full divide-y divide-gray-200">
						<thead class="bg-gray-50">
							<tr>
								<th
									class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase"
									>Nome</th
								>
								<th
									class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase"
									>E-mail</th
								>
								<th
									class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase"
									>Papel</th
								>
								<th class="px-4 py-3"></th>
							</tr>
						</thead>
						<tbody class="divide-y divide-gray-200">
							{#each users as user}
								<tr>
									<td class="px-4 py-3 text-gray-900">
										{user.username}
										{#if user.is_admin}
											<span
												class="ml-1 text-xs bg-gray-100 text-gray-700 px-2 py-0.5 rounded-full"
												>Admin</span
											>
										{/if}
										{#if user.is_deleted}
											<span
												class="ml-1 text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full"
												>Excluído</span
											>
										{/if}
									</td>
									<td class="px-4 py-3 text-gray-600"
										>{user.email}</td
									>
									<td class="px-4 py-3">
										{#if user.is_candidate}
											<span
												class="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full"
												>Candidato</span
											>
										{:else}
											<span
												class="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full"
												>Eleitor</span
											>
										{/if}
									</td>
									<td
										class="px-4 py-3 text-right whitespace-nowrap space-x-2"
									>
										{#if user.is_deleted}
											<button
												on:click={() =>
													reactivateUser(user)}
												class="text-sm px-3 py-1 rounded-md border border-gray-300 hover:bg-gray-50"
											>
												Reativar
											</button>
										{:else}
											<button
												on:click={() =>
													toggleCandidate(user)}
												class="text-sm px-3 py-1 rounded-md border border-gray-300 hover:bg-gray-50"
											>
												{user.is_candidate
													? "Tornar eleitor"
													: "Tornar candidato"}
											</button>
											{#if !user.is_admin}
												<button
													on:click={() =>
														deleteUser(user)}
													class="text-sm px-3 py-1 rounded-md text-red-600 hover:bg-red-50"
												>
													Excluir
												</button>
											{/if}
										{/if}
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{/if}
		</section>

		<section>
			<h2 class="text-2xl font-bold text-gray-900 mb-4">Eleições</h2>

			<form
				class="flex flex-wrap gap-2 mb-6"
				on:submit|preventDefault={createElection}
			>
				<label for="new-election" class="sr-only"
					>Título da eleição</label
				>
				<input
					id="new-election"
					bind:value={newElectionTitle}
					placeholder="Título da nova eleição"
					class="flex-1 min-w-0 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
				/>
				<button
					type="submit"
					class="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
				>
					Criar eleição
				</button>
			</form>

			{#if elections.length === 0 && !loading}
				<div class="text-gray-500">Nenhuma eleição cadastrada</div>
			{/if}

			<div class="grid gap-4 md:grid-cols-2">
				{#each elections as election}
					<div class="bg-white shadow rounded-lg p-5 space-y-4">
						<div class="flex justify-between items-start gap-2">
							<div class="flex flex-wrap items-center gap-2">
								<h3 class="text-lg font-medium text-gray-900">
									{election.title}
								</h3>
								<ElectionStatusBadge status={election.status} />
							</div>
							{#if election.has_votes && (election.status === "open" || election.status === "closed")}
								<button
									on:click={() => cancelElection(election)}
									class="text-sm text-red-600 hover:text-red-500"
								>
									Cancelar eleição
								</button>
							{:else if !election.has_votes && election.status !== "tallied"}
								<button
									on:click={() => deleteElection(election)}
									class="text-sm text-red-600 hover:text-red-500"
								>
									Excluir
								</button>
							{/if}
						</div>

						{#if election.status === "draft"}
							<button
								on:click={() => openElection(election)}
								disabled={election.candidates.length < 2}
								class="w-full bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed"
							>
								Abrir votação
							</button>
							{#if election.candidates.length < 2}
								<p class="text-xs text-gray-500 -mt-2">
									Vincule ao menos 2 candidatos para abrir a
									votação.
								</p>
							{/if}
						{:else if election.status === "open"}
							<button
								on:click={() => closeElection(election)}
								class="w-full bg-yellow-500 text-white px-4 py-2 rounded-md hover:bg-yellow-600 focus:outline-none focus:ring-2 focus:ring-yellow-400"
							>
								Encerrar eleição
							</button>
						{:else if election.status === "closed"}
							<button
								on:click={() => tallyElection(election)}
								class="w-full bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
							>
								Apurar votos
							</button>
						{/if}

						{#if election.status === "tallied" && results[election.id]}
							<ElectionResults results={results[election.id]} />
						{:else}
							{#if election.candidates.length === 0}
								<p class="text-sm text-gray-500">
									Nenhum candidato vinculado
								</p>
							{:else}
								<ul class="divide-y divide-gray-100">
									{#each election.candidates as candidate}
										<li
											class="flex justify-between items-center py-2"
										>
											<span
												>{candidate.username}
												{#if candidate.is_deleted}
													<span
														class="text-xs text-gray-500"
														>(conta excluída)</span
													>
												{/if}
											</span>
											{#if election.status === "draft"}
												<button
													on:click={() =>
														removeCandidate(
															election,
															candidate,
														)}
													class="text-sm text-gray-500 hover:text-red-600"
												>
													Remover
												</button>
											{/if}
										</li>
									{/each}
								</ul>
							{/if}

							{#if election.status === "draft"}
								<div class="flex gap-2">
									<label
										for="candidate-{election.id}"
										class="sr-only">Candidato</label
									>
									<select
										id="candidate-{election.id}"
										bind:value={selectedCandidate[election.id]}
										class="flex-1 min-w-0 px-3 py-2 border border-gray-300 rounded-md"
									>
										<option value="">Selecione um candidato</option>
										{#each availableCandidates(election) as candidate}
											<option value={candidate.id}
												>{candidate.username}</option
											>
										{/each}
									</select>
									<button
										on:click={() => addCandidate(election)}
										disabled={!selectedCandidate[election.id]}
										class="bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 disabled:opacity-50"
									>
										Vincular
									</button>
								</div>
							{/if}
						{/if}
					</div>
				{/each}
			</div>
		</section>
	</main>
</div>
