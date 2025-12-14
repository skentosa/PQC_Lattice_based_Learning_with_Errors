import numpy as np

class LWE:
    def __init__(self, n, q, stddev):
        self.n = n  # dimension of the lattice
        self.q = q  # modulus
        self.stddev = stddev  # standard deviation for error distribution
        
    def generate_keys(self):
        # Secret key
        self.s = np.random.randint(0, self.q, self.n)
    
        # Public key (A, b)
        self.A = np.random.randint(0, self.q, (self.n, self.n))
    
        # Βελτιωμένη Δειγματοληψία Σφάλματος
        # 1. Δειγματοληπτήστε από κανονική
        e_float = np.random.normal(0, self.stddev, self.n)
        # 2. Περιορίστε (clip) τις τιμές σε ένα λογικό εύρος (π.χ., ± 2*stddev)
        bound = 2 * self.stddev
        e_clipped = np.clip(e_float, -bound, bound)
        # 3. Στρογγυλοποιήστε και μετατρέψτε σε ακέραιο
        self.e = np.round(e_clipped).astype(int)
    
        # 4. Υπολογίστε το b
        self.b = (np.dot(self.A, self.s) + self.e) % self.q
    
        return (self.A, self.b), self.s
    
    def encrypt(self, public_key, m):
        A, b = public_key
        r = np.random.randint(0, 2, self.n)
        
        u = np.matmul(A.T, r) % self.q 
        v = (np.dot(b, r) + m * (self.q // 2)) % self.q
        
        return (u, v)
    
    def decrypt(self, ciphertext):
        u, v = ciphertext
        diff = (v - np.dot(self.s, u)) % self.q
        return 1 if abs(diff - self.q / 2) < self.q / 4 else 0
    