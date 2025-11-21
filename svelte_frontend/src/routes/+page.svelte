<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { auth } from '../lib/stores/auth';

	onMount(() => {
		if ($auth.isAuthenticated) {
			goto('/election');
		} else {
			goto('/login');
		}
	});
</script>

<div class="min-h-screen flex items-center justify-center bg-gray-50">
	<div class="text-center">
		<h1 class="text-3xl font-bold text-gray-900 mb-4">Sistema de Eleições</h1>
		<p class="text-gray-600">Redirecionando...</p>
	</div>
</div>
