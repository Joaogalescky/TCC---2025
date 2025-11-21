<script lang="ts">
	import { api, ApiError } from '../../lib/api';
	import { goto } from '$app/navigation';

	let username = '';
	let email = '';
	let password = '';
	let confirmPassword = '';
	let error = '';
	let loading = false;

	async function handleRegister() {
		if (!username || !email || !password || !confirmPassword) {
			error = 'Preencha todos os campos';
			return;
		}

		if (password !== confirmPassword) {
			error = 'Senhas não coincidem';
			return;
		}

		loading = true;
		error = '';

		try {
			await api.register({ username, email, password });
			goto('/login');
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Erro no cadastro';
		} finally {
			loading = false;
		}
	}
</script>

<div class="min-h-screen flex items-center justify-center bg-gray-50">
	<div class="max-w-md w-full space-y-8">
		<div>
			<h2 class="mt-6 text-center text-3xl font-extrabold text-gray-900">
				Criar nova conta
			</h2>
		</div>
		<form class="mt-8 space-y-6" on:submit|preventDefault={handleRegister}>
			<div class="space-y-4">
				<div>
					<label for="username" class="block text-sm font-medium text-gray-700">Nome de usuário</label>
					<input
						id="username"
						type="text"
						bind:value={username}
						required
						class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
					/>
				</div>
				<div>
					<label for="email" class="block text-sm font-medium text-gray-700">Email</label>
					<input
						id="email"
						type="email"
						bind:value={email}
						required
						class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
					/>
				</div>
				<div>
					<label for="password" class="block text-sm font-medium text-gray-700">Senha</label>
					<input
						id="password"
						type="password"
						bind:value={password}
						required
						class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
					/>
				</div>
				<div>
					<label for="confirmPassword" class="block text-sm font-medium text-gray-700">Confirmar senha</label>
					<input
						id="confirmPassword"
						type="password"
						bind:value={confirmPassword}
						required
						class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
					/>
				</div>
			</div>

			{#if error}
				<div class="text-red-600 text-sm text-center">{error}</div>
			{/if}

			<div>
				<button
					type="submit"
					disabled={loading}
					class="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
				>
					{loading ? 'Cadastrando...' : 'Cadastrar'}
				</button>
			</div>

			<div class="text-center">
				<a href="/login" class="text-blue-600 hover:text-blue-500">Já tem conta? Faça login</a>
			</div>
		</form>
	</div>
</div>