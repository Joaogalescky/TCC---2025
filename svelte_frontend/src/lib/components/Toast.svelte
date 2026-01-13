<script lang="ts">
	interface Props {
		message: string;
		type: "success" | "error";
	}

	let { message, type }: Props = $props();
</script>

{#if message}
	<div class="fixed top-20 right-4 z-50 animate-slide-in">
		<div
			class="flex items-center p-4 rounded-xl text-base shadow-lg {type === 'success'
				? 'bg-emerald-50 text-emerald-500 border border-emerald-400'
				: 'bg-red-400 text-white-400 border border-red-400 text-white'}"
			role="alert"
		>
			<svg
				class="w-5 h-5 mr-2"
				viewBox="0 0 20 20"
				fill="none"
				xmlns="http://www.w3.org/2000/svg"
			>
				<path
					d="M10.0043 13.3333V9.16663M9.99984 6.66663H10.0073M9.99984 18.3333C5.39746 18.3333 1.6665 14.6023 1.6665 9.99996C1.6665 5.39759 5.39746 1.66663 9.99984 1.66663C14.6022 1.66663 18.3332 5.39759 18.3332 9.99996C18.3332 14.6023 14.6022 18.3333 9.99984 18.3333Z"
					stroke={type === 'success' ? '#10B981' : '#fff'}
					stroke-width="1.5"
					stroke-linecap="round"
					stroke-linejoin="round"
				/>
			</svg>
			<span class="font-semibold mr-1">
				{type === 'success' ? 'Sucesso' : 'Erro'}
			</span>
			{message}
		</div>
	</div>
{/if}

<style>
	@keyframes slide-in {
		from {
			transform: translateX(100%);
			opacity: 0;
		}
		to {
			transform: translateX(0);
			opacity: 1;
		}
	}

	.animate-slide-in {
		animation: slide-in 0.3s ease-out;
	}
</style>
