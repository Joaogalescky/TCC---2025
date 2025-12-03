<script lang="ts">
	import { goto } from "$app/navigation";
	import { authActions } from "$lib/stores/auth";
	import { api, ApiError } from "../../lib/api";

	let username = "";
	let email = "";
	let password = "";
	let confirmPassword = "";
	let error = "";
	let loading = false;
	let showPassword = false;

	async function handleRegister() {
		if (!username || !email || !password || !confirmPassword) {
			error = "Preencha todos os campos";
			return;
		}

		if (password !== confirmPassword) {
			error = "Senhas não coincidem";
			return;
		}

		loading = true;
		error = "";

		try {
			await api.register({ username, email, password });
			const loginResponse = await api.login(email, password);

			if (loginResponse.access_token) {
				const user = { id: 1, username, email, statusVotacao: false };
				authActions.login(loginResponse.access_token, user);
				goto("/election");
			}
		} catch (e) {
			error = e instanceof ApiError ? e.message : "Erro no cadastro";
		} finally {
			loading = false;
		}
	}
</script>

<div class="min-h-screen flex items-center justify-center bg-gray-50">
	<div class="max-w-md w-full space-y-8">
		<div>
			<h2 class="mt-6 text-center text-3xl font-extrabold text-gray-900">
				Criar conta
			</h2>
		</div>
		<form class="mt-8 space-y-6" on:submit|preventDefault={handleRegister}>
			<div class="space-y-4">
				<div>
					<label
						for="username"
						class="block text-sm font-medium text-gray-700"
					></label>
					<input
						id="username"
						type="text"
						placeholder="Usuário"
						minlength="4"
						maxlength="45"
						bind:value={username}
						required
						class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
					/>
				</div>
				<div>
					<label
						for="email"
						class="block text-sm font-medium text-gray-700"
					></label>
					<input
						id="email"
						type="email"
						placeholder="E-mail"
						bind:value={email}
						on:input={(e) =>
							(email = e.currentTarget.value.toLowerCase())}
						required
						class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
					/>
				</div>
				<div>
					<label
						for="password"
						class="block text-sm font-medium text-gray-700"
					></label>
					<div class="relative">
						<input
							id="password"
							type={showPassword ? "text" : "password"}
							placeholder="Senha"
							minlength="6"
							bind:value={password}
							required
							class="mt-1 block w-full px-3 py-2 pr-10 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
						/>
						<button
							type="button"
							on:click={() => showPassword = !showPassword}
							class="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 hover:text-gray-600"
						>
							{#if showPassword}
								<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
								</svg>
							{:else}
								<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
								</svg>
							{/if}
						</button>
					</div>
				</div>
				<div>
					<label
						for="confirmPassword"
						class="block text-sm font-medium text-gray-700"
					></label>
					<div class="relative">
						<input
							id="confirmPassword"
							type={showPassword ? "text" : "password"}
							placeholder="Confirmar senha"
							minlength="6"
							bind:value={confirmPassword}
							required
							class="mt-1 block w-full px-3 py-2 pr-10 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
						/>
						<button
							type="button"
							on:click={() => showPassword = !showPassword}
							class="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 hover:text-gray-600"
						>
							{#if showPassword}
								<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
								</svg>
							{:else}
								<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
								</svg>
							{/if}
						</button>
					</div>
				</div>
			</div>

			{#if error}
				<div class="text-red-400 text-base text-center">{error}</div>
			{/if}

			<div>
				<button
					type="submit"
					disabled={loading}
					class="group relative w-full flex justify-center py-2 px-4 border border-transparent text-base font-bold rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
				>
					{loading ? "Cadastrando..." : "Cadastrar"}
				</button>
			</div>

			<div class="text-center">
				<a
					href="/login"
					class="text-blue-600 hover:text-blue-700 text-base"
					>Já tem conta? Faça login</a
				>
			</div>
		</form>
	</div>
</div>
