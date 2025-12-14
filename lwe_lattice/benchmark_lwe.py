import numpy as np
import time
import json
import psutil
import matplotlib.pyplot as plt

class LWE:
    def __init__(self, n, q, stddev):
        self.n = n
        self.q = q
        self.stddev = stddev
        
    def generate_keys(self):
        self.s = np.random.randint(0, self.q, self.n)
        self.A = np.random.randint(0, self.q, (self.n, self.n))
        self.e = np.round(np.random.normal(0, self.stddev, self.n)).astype(int) % self.q
        self.b = (np.dot(self.A, self.s) + self.e) % self.q
        return (self.A, self.b), self.s
    
    def encrypt(self, public_key, m):
        A, b = public_key
        r = np.random.randint(0, 2, self.n)
        u = np.dot(A.T, r) % self.q
        v = (np.dot(b, r) + m * (self.q // 2)) % self.q
        return (u, v)
    
    def decrypt(self, ciphertext):
        u, v = ciphertext
        return int((v - np.dot(self.s, u)) % self.q > self.q // 2)

def np_to_json(data):
    if isinstance(data, tuple):
        return {'type': 'tuple', 'data': [np_to_json(item) for item in data]}
    elif isinstance(data, np.ndarray):
        return {'type': 'ndarray', 'data': data.astype(object).tolist()}
    elif isinstance(data, np.integer):
        return int(data)
    return data

def get_serialized_size(data):
    json_data = json.dumps(np_to_json(data))
    return len(json_data.encode('utf-8'))

def estimate_security(n, q):
    if n <= 64:
        return {"classical_bits": "~60", "quantum_bits": "~30"}
    elif n <= 128:
        return {"classical_bits": "~100", "quantum_bits": "~50"}
    elif n <= 256:
        return {"classical_bits": "128" if q >= 3329 else "~110", "quantum_bits": "~64" if q >= 3329 else "~55"}
    elif n <= 512:
        return {"classical_bits": "192" if q >= 3329 else "~170", "quantum_bits": "~96" if q >= 3329 else "~85"}
    else:
        return {"classical_bits": "High", "quantum_bits": "High"}

def benchmark_lwe(n, q=3329, stddev=1.0, trials=1000):
    results = {
        "n": n,
        "q": q,
        "stddev": stddev,
        "key_gen_time": 0,
        "encrypt_time": 0,
        "decrypt_time": 0,
        "public_key_size": 0,
        "ciphertext_size": 0,
        "error_rate": 0,
        "memory_usage": 0,
        "security_estimate": estimate_security(n, q)
    }
    
    lwe = LWE(n, q, stddev)
    
    key_gen_times = []
    for _ in range(trials):
        start = time.time()
        public_key, secret_key = lwe.generate_keys()
        key_gen_times.append(time.time() - start)
    results["key_gen_time"] = np.mean(key_gen_times)
    
    enc_times = []
    dec_times = []
    errors = 0
    for _ in range(trials):
        message = np.random.randint(0, 2)
        start = time.time()
        ciphertext = lwe.encrypt(public_key, message)
        enc_times.append(time.time() - start)
        
        start = time.time()
        decrypted = lwe.decrypt(ciphertext)
        dec_times.append(time.time() - start)
        
        if decrypted != message:
            errors += 1
    
    results["encrypt_time"] = np.mean(enc_times)
    results["decrypt_time"] = np.mean(dec_times)
    results["error_rate"] = errors / trials
    
    results["public_key_size"] = get_serialized_size(public_key)
    results["ciphertext_size"] = get_serialized_size(ciphertext)
    
    process = psutil.Process()
    results["memory_usage"] = process.memory_info().rss / (1024 * 1024)
    
    return results

# Run benchmarks for combinations of n, q, and stddev
ns = [64, 128, 256, 512]
qs = [3329, 7681, 12289]
stddevs = [0.5, 0.75, 1.0]
benchmarks = {}
for n in ns:
    for q in qs:
        for stddev in stddevs:
            key = f"n={n}_q={q}_stddev={stddev}"
            benchmarks[key] = benchmark_lwe(n, q, stddev)

# Save results to JSON for thesis
with open('benchmark_results.json', 'w') as f:
    json.dump(benchmarks, f, indent=2, default=str)

# Print results
for key, result in benchmarks.items():
    print(f"{key}: {result}")

# Plotting
plt.figure(figsize=(12, 8))
for q in qs:
    for stddev in stddevs:
        times = [benchmarks[f"n={n}_q={q}_stddev={stddev}"]["key_gen_time"] for n in ns]
        plt.plot(ns, times, marker='o', label=f'q={q}, stddev={stddev}')
plt.xlabel('n')
plt.ylabel('Key Generation Time (s)')
plt.title('Key Generation Time vs. n')
plt.legend()
plt.grid(True)
plt.savefig('key_gen_time.png')
plt.close()

plt.figure(figsize=(12, 8))
for q in qs:
    for stddev in stddevs:
        times = [benchmarks[f"n={n}_q={q}_stddev={stddev}"]["encrypt_time"] for n in ns]
        plt.plot(ns, times, marker='o', label=f'q={q}, stddev={stddev}')
plt.xlabel('n')
plt.ylabel('Encryption Time (s)')
plt.title('Encryption Time vs. n')
plt.legend()
plt.grid(True)
plt.savefig('encrypt_time.png')
plt.close()

plt.figure(figsize=(12, 8))
for q in qs:
    for stddev in stddevs:
        times = [benchmarks[f"n={n}_q={q}_stddev={stddev}"]["decrypt_time"] for n in ns]
        plt.plot(ns, times, marker='o', label=f'q={q}, stddev={stddev}')
plt.xlabel('n')
plt.ylabel('Decryption Time (s)')
plt.title('Decryption Time vs. n')
plt.legend()
plt.grid(True)
plt.savefig('decrypt_time.png')
plt.close()

plt.figure(figsize=(12, 8))
for q in qs:
    sizes = [benchmarks[f"n={n}_q={q}_stddev={stddevs[0]}"]["public_key_size"] / 1024 for n in ns]
    plt.plot(ns, sizes, marker='o', label=f'q={q}')
plt.xlabel('n')
plt.ylabel('Public Key Size (KB)')
plt.title('Public Key Size vs. n')
plt.legend()
plt.grid(True)
plt.savefig('public_key_size.png')
plt.close()

plt.figure(figsize=(12, 8))
for q in qs:
    sizes = [benchmarks[f"n={n}_q={q}_stddev={stddevs[0]}"]["ciphertext_size"] / 1024 for n in ns]
    plt.plot(ns, sizes, marker='o', label=f'q={q}')
plt.xlabel('n')
plt.ylabel('Ciphertext Size (KB)')
plt.title('Ciphertext Size vs. n')
plt.legend()
plt.grid(True)
plt.savefig('ciphertext_size.png')
plt.close()

plt.figure(figsize=(12, 8))
for q in qs:
    for stddev in stddevs:
        errors = [benchmarks[f"n={n}_q={q}_stddev={stddev}"]["error_rate"] for n in ns]
        plt.plot(ns, errors, marker='o', label=f'q={q}, stddev={stddev}')
plt.xlabel('n')
plt.ylabel('Error Rate')
plt.title('Error Rate vs. n')
plt.legend()
plt.grid(True)
plt.savefig('error_rate.png')
plt.close()

plt.figure(figsize=(12, 8))
for q in qs:
    memory = [benchmarks[f"n={n}_q={q}_stddev={stddevs[0]}"]["memory_usage"] for n in ns]
    plt.plot(ns, memory, marker='o', label=f'q={q}')
plt.xlabel('n')
plt.ylabel('Memory Usage (MB)')
plt.title('Memory Usage vs. n')
plt.legend()
plt.grid(True)
plt.savefig('memory_usage.png')
plt.close()