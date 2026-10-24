<script lang="ts">
	import { browser } from "$app/environment";
	import { goto } from "$app/navigation";
	import { onMount } from "svelte";
	import { api, ApiError, API_BASE } from "../../lib/api";
	import { auth, authActions } from "../../lib/stores/auth";
	import Toast from "$lib/components/Toast.svelte";
	import ElectionStatusBadge from "$lib/components/ElectionStatusBadge.svelte";
	import ElectionResults, {
		type ElectionResultsData,
	} from "$lib/components/ElectionResults.svelte";

	interface Election {
		id: number;
		title: string;
		status: string;
	}

	interface Candidate {
		id: number;
		username: string;
	}

	interface ElectionWithCandidates extends Election {
		candidates: Candidate[];
	}

	let elections: Election[] = [];
	let selectedElection: ElectionWithCandidates | null = null;
	// Resultado publicado da eleição selecionada (somente se apurada)
	let selectedResults: ElectionResultsData | null = null;
	let loading = false;
	let voting = false;
	let message = "";
	let messageType: "success" | "error" = "success";

	$: if (browser && !$auth.isAuthenticated) {
		goto("/login");
	}

	onMount(async () => {
		await loadElections();

		if (browser) {
			const eventSource = new EventSource(
				`${API_BASE}/events/elections`,
			);

			eventSource.onmessage = () => {
				loadElections();
				if (selectedElection) {
					selectElection(selectedElection);
				}
			};
			return () => {
				eventSource.close();
			};
		}
	});

	async function loadElections() {
		loading = true;
		try {
			const response = await api.getElections();
			elections = response.elections;
		} catch (e) {
			showMessage("Erro ao carregar eleições", "error");
		} finally {
			loading = false;
		}
	}

	async function selectElection(election: Election) {
		loading = true;
		try {
			selectedElection = await api.getElectionCandidates(election.id);
			selectedResults =
				selectedElection?.status === "tallied"
					? await api.getResults(election.id)
					: null;
		} catch (e) {
			showMessage("Erro ao carregar candidatos", "error");
		} finally {
			loading = false;
		}
	}

	async function vote(candidateId: number) {
		if (!selectedElection) return;

		voting = true;
		try {
			await api.vote(selectedElection.id, candidateId);
			showMessage("Voto registrado com sucesso!", "success");
			selectedElection = null;
		} catch (e) {
			const errorMsg =
				e instanceof ApiError ? e.message : "Erro ao votar";
			showMessage(errorMsg, "error");
		} finally {
			voting = false;
		}
	}

	async function openElection(election: Election) {
		if (
			!confirm(
				`Abrir a votação de "${election.title}"? Depois disso a lista de candidatos não poderá ser alterada.`,
			)
		)
			return;
		try {
			await api.openElection(election.id);
			showMessage("Votação aberta", "success");
			await refresh(election);
		} catch (e) {
			showMessage(
				e instanceof ApiError ? e.message : "Erro ao abrir a votação",
				"error",
			);
		}
	}

	async function closeElection(election: Election) {
		if (
			!confirm(
				`Encerrar "${election.title}"? Nenhum voto novo será aceito.`,
			)
		)
			return;
		try {
			await api.closeElection(election.id);
			showMessage("Eleição encerrada", "success");
			await refresh(election);
		} catch (e) {
			showMessage(
				e instanceof ApiError ? e.message : "Erro ao encerrar eleição",
				"error",
			);
		}
	}

	async function tallyElection(election: Election) {
		try {
			await api.tallyElection(election.id);
			showMessage("Votos apurados e resultado publicado", "success");
			await refresh(election);
		} catch (e) {
			showMessage(
				e instanceof ApiError ? e.message : "Erro ao apurar votos",
				"error",
			);
		}
	}

	async function refresh(election: Election) {
		await loadElections();
		if (selectedElection?.id === election.id) {
			await selectElection(election);
		}
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
					<h1 class="text-xl font-semibold">Sistema de Eleições</h1>
				</div>
				<div class="flex items-center space-x-4">
					{#if $auth.user?.is_admin}
						<a
							href="/admin"
							class="text-blue-600 hover:text-blue-500 font-bold"
						>
							Administração
						</a>
					{/if}
					<span class="text-gray-700"
						>Olá, {$auth.user?.username}
						{#if $auth.user?.is_candidate}
							<span
								class="ml-1 text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full"
								>Candidato</span
							>
						{/if}
					</span>
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

	<main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
		{#if !selectedElection}
			<div class="px-4 py-6 sm:px-0">
				<h2 class="text-2xl font-bold text-gray-900 mb-6">
					Eleições Disponíveis
				</h2>

				{#if loading}
					<div class="text-center py-8">
						<div class="text-gray-500">Carregando eleições...</div>
					</div>
				{:else if elections.length === 0}
					<div class="text-center py-8">
						<div class="text-gray-500">
							Nenhuma eleição disponível
						</div>
					</div>
				{:else}
					<div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
						{#each elections as election}
							<div
								class="bg-white overflow-hidden shadow rounded-lg"
							>
								<div class="px-4 py-5 sm:p-6">
									<div
										class="flex flex-wrap items-center justify-between gap-2 mb-4"
									>
										<h3
											class="text-lg font-medium text-gray-900"
										>
											{election.title}
										</h3>
										<ElectionStatusBadge
											status={election.status}
										/>
									</div>
									<button
										on:click={() =>
											selectElection(election)}
										class="w-full bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
									>
										{election.status === "tallied"
											? "Ver Resultado"
											: "Ver Candidatos"}
									</button>
									{#if $auth.user?.is_admin}
										{#if election.status === "draft"}
											<button
												on:click={() =>
													openElection(election)}
												class="mt-2 w-full bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500"
											>
												Abrir votação
											</button>
										{:else if election.status === "open"}
											<button
												on:click={() =>
													closeElection(election)}
												class="mt-2 w-full bg-yellow-500 text-white px-4 py-2 rounded-md hover:bg-yellow-600 focus:outline-none focus:ring-2 focus:ring-yellow-400"
											>
												Encerrar eleição
											</button>
										{:else if election.status === "closed"}
											<button
												on:click={() =>
													tallyElection(election)}
												class="mt-2 w-full bg-white text-blue-700 border border-blue-600 px-4 py-2 rounded-md hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
											>
												Apurar votos
											</button>
										{/if}
									{/if}
								</div>
							</div>
						{/each}
					</div>
				{/if}
			</div>
		{:else}
			<div class="px-4 py-6 sm:px-0">
				<div class="mb-6">
					<button
						on:click={() => (selectedElection = null)}
						class="text-blue-600 hover:text-blue-500"
					>
						← Voltar às eleições
					</button>
				</div>

				<div class="flex flex-wrap items-center gap-3 mb-6">
					<h2 class="text-2xl font-bold text-gray-900">
						{selectedElection.title}
					</h2>
					<ElectionStatusBadge status={selectedElection.status} />
					{#if $auth.user?.is_admin}
						{#if selectedElection.status === "draft"}
							<button
								on:click={() =>
									selectedElection &&
									openElection(selectedElection)}
								class="ml-auto bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500"
							>
								Abrir votação
							</button>
						{:else if selectedElection.status === "open"}
							<button
								on:click={() =>
									selectedElection &&
									closeElection(selectedElection)}
								class="ml-auto bg-yellow-500 text-white px-4 py-2 rounded-md hover:bg-yellow-600 focus:outline-none focus:ring-2 focus:ring-yellow-400"
							>
								Encerrar eleição
							</button>
						{:else if selectedElection.status === "closed"}
							<button
								on:click={() =>
									selectedElection &&
									tallyElection(selectedElection)}
								class="ml-auto bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
							>
								Apurar votos
							</button>
						{/if}
					{/if}
				</div>

				{#if selectedElection.status === "draft"}
					<p
						class="mb-6 text-sm bg-gray-50 text-gray-700 border border-gray-200 rounded-md px-4 py-3"
					>
						Eleição em configuração. A votação ainda não foi aberta
						pelo administrador.
					</p>
				{:else if selectedElection.status === "closed"}
					<p
						class="mb-6 text-sm bg-yellow-50 text-yellow-800 border border-yellow-200 rounded-md px-4 py-3"
					>
						Votação encerrada. O resultado será publicado após a
						apuração.
					</p>
				{/if}

				{#if loading}
					<div class="text-center py-8">
						<div class="text-gray-500">
							Carregando candidatos...
						</div>
					</div>
				{:else if selectedResults}
					<div class="bg-white shadow rounded-lg p-6 max-w-2xl">
						<h3 class="text-lg font-medium text-gray-900 mb-4">
							Resultado da apuração
						</h3>
						<ElectionResults results={selectedResults} />
					</div>
				{:else if selectedElection.candidates.length === 0}
					<div class="text-center py-8">
						<div class="text-gray-500">
							Nenhum candidato disponível
						</div>
					</div>
				{:else}
					<div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
						{#each selectedElection.candidates as candidate}
							<div
								class="bg-white overflow-hidden shadow rounded-lg"
							>
								<div class="px-4 py-5 sm:p-6">
									<h3
										class="text-lg font-medium text-gray-900 mb-4"
									>
										{candidate.username}
									</h3>
									{#if selectedElection.status === "open"}
										<button
											on:click={() => vote(candidate.id)}
											disabled={voting}
											class="w-full bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 disabled:opacity-50"
										>
											{voting ? "Votando..." : "Votar"}
										</button>
									{/if}
								</div>
							</div>
						{/each}
					</div>
				{/if}
			</div>
		{/if}
	</main>
</div>
