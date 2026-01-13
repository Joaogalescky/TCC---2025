<script lang="ts">
	import { browser } from "$app/environment";
	import { goto } from "$app/navigation";
	import { onMount } from "svelte";
	import { api, ApiError } from "../../lib/api";
	import { auth, authActions } from "../../lib/stores/auth";
	import Toast from "$lib/components/Toast.svelte";

	interface Election {
		id: number;
		title: string;
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
				"http://localhost:8000/events/elections",
			);

			eventSource.onmessage = () => {
				loadElections();
				if (selectedElection) {
					selectElection({
						id: selectedElection.id,
						title: selectedElection.title,
					});
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
									<h3
										class="text-lg font-medium text-gray-900 mb-4"
									>
										{election.title}
									</h3>
									<button
										on:click={() =>
											selectElection(election)}
										class="w-full bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
									>
										Ver Candidatos
									</button>
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

				<h2 class="text-2xl font-bold text-gray-900 mb-6">
					{selectedElection.title}
				</h2>

				{#if loading}
					<div class="text-center py-8">
						<div class="text-gray-500">
							Carregando candidatos...
						</div>
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
									<button
										on:click={() => vote(candidate.id)}
										disabled={voting}
										class="w-full bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 disabled:opacity-50"
									>
										{voting ? "Votando..." : "Votar"}
									</button>
								</div>
							</div>
						{/each}
					</div>
				{/if}
			</div>
		{/if}
	</main>
</div>
