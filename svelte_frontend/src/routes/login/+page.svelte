<script lang="ts">
	import { goto } from "$app/navigation";
	import { api, ApiError } from "../../lib/api";
	import { authActions } from "../../lib/stores/auth";

	let email = "";
	let password = "";
	let error = "";
	let loading = false;

	async function handleLogin() {
		if (!email || !password) {
			error = "Preencha todos os campos";
			return;
		}

		loading = true;
		error = "";

		try {
			const response = await api.login(email, password);

			if (response.access_token) {
				// Get user info (simplified - in real app you'd decode JWT or make another request)
				const user = {
					id: 1,
					username: email.split("@")[0],
					email,
					statusVotacao: false,
				};
				authActions.login(response.access_token, user);
				goto("/election");
			} else {
				error = "Credenciais inválidas";
			}
		} catch (e) {
			error = e instanceof ApiError ? e.message : "Erro no login";
		} finally {
			loading = false;
		}
	}
</script>

<div class="min-h-screen flex items-center justify-center bg-gray-50">
	<div class="max-w-md w-full space-y-8">
		<div>
			<h2 class="mt-6 text-center text-3xl font-extrabold text-gray-900">
				Fazer Login
			</h2>
		</div>
		<form class="mt-8 space-y-6" on:submit|preventDefault={handleLogin}>
			<div class="space-y-4">
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
						class="block text-base font-medium text-gray-700"
					></label>
					<input
						id="password"
						type="password"
						placeholder="Senha"
						minlength="6"
						bind:value={password}
						required
						class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
					/>
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
					{loading ? "Entrando..." : "Entrar"}
				</button>
			</div>

			<div class="text-center">
				<a
					href="/register"
					class="text-blue-600 hover:text-blue-700 text-base"
					>Não tem conta? Cadastre-se</a
				>
			</div>
		</form>
	</div>
</div>
