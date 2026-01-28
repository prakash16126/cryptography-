import time
import os
from statistics import mean
from Cryptodome.Cipher import AES, DES3
from Cryptodome.Random import get_random_bytes
from Cryptodome.Util.Padding import pad, unpad
import hashlib
import matplotlib.pyplot as plt
import numpy as np
import base64
from my_cryptography_project.encryption_app.crypto_hybrid import HybridCrypto


def benchmark(func, data_gen, trials=5):
    durs = []
    for _ in range(trials):
        data = data_gen()
        t0 = time.perf_counter()
        func(data)
        durs.append(time.perf_counter() - t0)
    return {
        "avg_sec": mean(durs),
        "min_sec": min(durs),
        "max_sec": max(durs),
    }

def generate_des3_key():
    """Generate a DES3 key as used in the original views.py"""
    return get_random_bytes(24)  # DES3 requires 24 bytes key

def run_original_des3_encrypt(data):
    """Benchmark the original DES3 encryption from views.py"""
    key = generate_des3_key()
    cipher = DES3.new(key, DES3.MODE_EAX)
    ciphertext, tag = cipher.encrypt_and_digest(data)
    # In the original views.py, we would write:
    # nonce + tag + ciphertext
    return {"key": key, "nonce": cipher.nonce, "tag": tag, "ciphertext": ciphertext}


def run_aes_cbc_encrypt(data):
    key = get_random_bytes(32)
    iv = get_random_bytes(16)
    cipher = AES.new(key, AES.MODE_CBC, iv=iv)
    _ = cipher.encrypt(pad(data, 16))


def run_aes_gcm_encrypt(data):
    key = get_random_bytes(32)
    cipher = AES.new(key, AES.MODE_GCM)
    _ct, _tag = cipher.encrypt_and_digest(data)


def run_hybrid_encrypt(data):
    base_key, des3_key = HybridCrypto.generate_keys()
    hybrid = HybridCrypto(base_key, des3_key)
    _ = hybrid.encrypt(data)


def bytes_per_sec(size_bytes, sec):
    return size_bytes / sec


def mb_per_sec(size_bytes, sec):
    return bytes_per_sec(size_bytes, sec) / (1024 * 1024)


def main():
    sizes = [1024, 1024 * 1024, 10 * 1024 * 1024]  # 1KB, 1MB, 10MB
    trials = 5
    print("Benchmarking Original DES3 vs AES vs Hybrid (DES3-derived AES-GCM)")
    print("Sizes:", sizes)
    print("Trials per test:", trials)
    print("")

    results = {}
    for size in sizes:
        def gen():
            return os.urandom(size)

        des3 = benchmark(run_original_des3_encrypt, gen, trials)
        cbc = benchmark(run_aes_cbc_encrypt, gen, trials)
        gcm = benchmark(run_aes_gcm_encrypt, gen, trials)
        hyb = benchmark(run_hybrid_encrypt, gen, trials)

        results[size] = {'des3': des3, 'cbc': cbc, 'gcm': gcm, 'hybrid': hyb}

        print(f"Size: {size} bytes")
        print(f"  Original DES3: avg {des3['avg_sec']:.6f}s | min {des3['min_sec']:.6f}s | max {des3['max_sec']:.6f}s | throughput {mb_per_sec(size, des3['avg_sec']):.2f} MB/s")
        print(f"  AES-CBC enc: avg {cbc['avg_sec']:.6f}s | min {cbc['min_sec']:.6f}s | max {cbc['max_sec']:.6f}s | throughput {mb_per_sec(size, cbc['avg_sec']):.2f} MB/s")
        print(f"  AES-GCM enc: avg {gcm['avg_sec']:.6f}s | min {gcm['min_sec']:.6f}s | max {gcm['max_sec']:.6f}s | throughput {mb_per_sec(size, gcm['avg_sec']):.2f} MB/s")
        print(f"  Hybrid enc : avg {hyb['avg_sec']:.6f}s | min {hyb['min_sec']:.6f}s | max {hyb['max_sec']:.6f}s | throughput {mb_per_sec(size, hyb['avg_sec']):.2f} MB/s")
        print("")

    # Correctness sanity check for HybridCrypto
    base_key, des3_key = HybridCrypto.generate_keys()
    hybrid = HybridCrypto(base_key, des3_key)
    sample = os.urandom(1024 * 1024)
    enc = hybrid.encrypt(sample)
    dec = hybrid.decrypt(enc["salt"], enc["nonce"], enc["ciphertext"], enc["tag"])
    assert dec == sample, "Hybrid decrypt mismatch!"
    print("Hybrid correctness check: PASS")
    
    # Generate performance comparison plots
    generate_plots(results)


def generate_plots(results):
    """Generate performance comparison plots"""
    sizes = list(results.keys())
    size_labels = [f"{s//1024}KB" if s < 1024*1024 else f"{s//(1024*1024)}MB" for s in sizes]
    
    # Extract throughput data
    des3_throughput = [mb_per_sec(size, results[size]['des3']['avg_sec']) for size in sizes]
    cbc_throughput = [mb_per_sec(size, results[size]['cbc']['avg_sec']) for size in sizes]
    gcm_throughput = [mb_per_sec(size, results[size]['gcm']['avg_sec']) for size in sizes]
    hybrid_throughput = [mb_per_sec(size, results[size]['hybrid']['avg_sec']) for size in sizes]
    
    # Create figure with subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # Throughput comparison
    x = np.arange(len(sizes))
    width = 0.2
    
    ax1.bar(x - width*1.5, des3_throughput, width, label='Original DES3', alpha=0.8, color='#1f77b4')
    ax1.bar(x - width/2, cbc_throughput, width, label='AES-CBC', alpha=0.8, color='#ff7f0e')
    ax1.bar(x + width/2, gcm_throughput, width, label='AES-GCM', alpha=0.8, color='#2ca02c')
    ax1.bar(x + width*1.5, hybrid_throughput, width, label='Hybrid (DES3+AES-GCM)', alpha=0.8, color='#d62728')
    
    ax1.set_xlabel('Data Size')
    ax1.set_ylabel('Throughput (MB/s)')
    ax1.set_title('Encryption Throughput Comparison')
    ax1.set_xticks(x)
    ax1.set_xticklabels(size_labels)
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Latency comparison
    des3_latency = [results[size]['des3']['avg_sec'] * 1000 for size in sizes]  # Convert to ms
    cbc_latency = [results[size]['cbc']['avg_sec'] * 1000 for size in sizes]
    gcm_latency = [results[size]['gcm']['avg_sec'] * 1000 for size in sizes]
    hybrid_latency = [results[size]['hybrid']['avg_sec'] * 1000 for size in sizes]
    
    ax2.plot(size_labels, des3_latency, 'D-', label='Original DES3', linewidth=2, markersize=8)
    ax2.plot(size_labels, cbc_latency, 'o-', label='AES-CBC', linewidth=2, markersize=8)
    ax2.plot(size_labels, gcm_latency, 's-', label='AES-GCM', linewidth=2, markersize=8)
    ax2.plot(size_labels, hybrid_latency, '^-', label='Hybrid (DES3+AES-GCM)', linewidth=2, markersize=8)
    
    ax2.set_xlabel('Data Size')
    ax2.set_ylabel('Latency (ms)')
    ax2.set_title('Encryption Latency Comparison')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax2.set_yscale('log')  # Log scale for better visualization
    
    plt.tight_layout()
    plt.savefig('crypto_performance_comparison.png', dpi=300, bbox_inches='tight')
    plt.show()
    print("\nPerformance comparison graph saved as 'crypto_performance_comparison.png'")
    
    # Create a separate plot comparing original DES3 vs Hybrid
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # Throughput comparison - DES3 vs Hybrid
    x = np.arange(len(sizes))
    width = 0.35
    
    ax1.bar(x - width/2, des3_throughput, width, label='Original DES3 (views.py)', alpha=0.8, color='#1f77b4')
    ax1.bar(x + width/2, hybrid_throughput, width, label='Hybrid (DES3+AES-GCM)', alpha=0.8, color='#d62728')
    
    ax1.set_xlabel('Data Size')
    ax1.set_ylabel('Throughput (MB/s)')
    ax1.set_title('Original vs New: Encryption Throughput Comparison')
    ax1.set_xticks(x)
    ax1.set_xticklabels(size_labels)
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Latency comparison - DES3 vs Hybrid
    ax2.plot(size_labels, des3_latency, 'D-', label='Original DES3 (views.py)', linewidth=2, markersize=8, color='#1f77b4')
    ax2.plot(size_labels, hybrid_latency, '^-', label='Hybrid (DES3+AES-GCM)', linewidth=2, markersize=8, color='#d62728')
    
    ax2.set_xlabel('Data Size')
    ax2.set_ylabel('Latency (ms)')
    ax2.set_title('Original vs New: Encryption Latency Comparison')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax2.set_yscale('log')  # Log scale for better visualization
    
    plt.tight_layout()
    plt.savefig('views_vs_hybrid_comparison.png', dpi=300, bbox_inches='tight')
    plt.show()
    print("Original DES3 vs Hybrid comparison graph saved as 'views_vs_hybrid_comparison.png'")


if __name__ == "__main__":
    main()